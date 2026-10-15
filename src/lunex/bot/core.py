"""LunexBot: takes one message (plus the recent conversation) and streams back events.

Events are plain dicts:
  {"type": "status", "text": "Searching the web..."}      progress for the app to show
  {"type": "delta",  "text": "..."}                       a piece of the reply (join them all together)
  {"type": "done",   "skill": "...", "sources": [...]}    finished
  {"type": "error",  "message": "..."}                    could not answer (message is safe to show)
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from lunex.ai.router import AllProvidersFailed, ProviderRouter
from lunex.bot import persona, research, summarize
from lunex.bot.calc import CalcError, calculate
from lunex.bot.commands import Intent, detect, time_answer, valid_tz
from lunex.bot.knowledge import KnowledgeBase
from lunex.config import Settings
from lunex.web.fetch import UnsafeURL, fetch_page, find_urls
from lunex.web.search import web_search

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean(text: str, limit: int) -> str:
    return _CONTROL.sub("", text or "").strip()[:limit]


class LunexBot:
    def __init__(self, router: ProviderRouter, settings: Settings, kb: Optional[KnowledgeBase] = None,
                 search_fn=web_search, fetch_fn=fetch_page):
        self.router, self.s = router, settings
        self.kb = kb or KnowledgeBase(settings.lunex_knowledge_dir)
        self.search_fn, self.fetch_fn = search_fn, fetch_fn

    # ---------- helpers ----------
    def _contact(self) -> str:
        return self.s.lunex_support_contact or "the app's operator (the contact email is under Settings > Legal)"

    def _history(self, history: List[Dict[str, str]], keep: int) -> List[Dict[str, str]]:
        out = []
        for t in history[-keep:]:
            role = "assistant" if t.get("role") == "assistant" else "user"
            content = clean(t.get("content", ""), 1500)
            if content:
                out.append({"role": role, "content": content})
        while out and out[0]["role"] != "user":
            out.pop(0)
        return out

    def _messages(self, req: Dict[str, Any], extra_system: str, user_content: str, keep: Optional[int] = None) -> List[Dict[str, str]]:
        now = datetime.now(valid_tz(req.get("tz")))
        system = persona.system_prompt(self.s, now, req.get("locale")) + (("\n\n" + extra_system) if extra_system else "")
        hist = self._history(req.get("history") or [], self.s.lunex_max_history if keep is None else keep)
        return [{"role": "system", "content": system}, *hist, {"role": "user", "content": user_content}]

    async def _llm(self, messages, *, temperature: float, skill: str, sources=None) -> AsyncIterator[dict]:
        total = 0
        try:
            async for piece in self.router.chat_stream(messages, {"max_tokens": self.s.lunex_max_output_tokens, "temperature": temperature}):
                total += len(piece)
                if total > 6000:
                    break
                yield {"type": "delta", "text": piece}
        except AllProvidersFailed as e:
            yield {"type": "error", "message": str(e)}
            return
        yield {"type": "done", "skill": skill, "sources": sources or []}

    @staticmethod
    def _say(text: str, skill: str, sources=None) -> List[dict]:
        return [{"type": "delta", "text": text}, {"type": "done", "skill": skill, "sources": sources or []}]

    # ---------- main entry ----------
    async def respond(self, req: Dict[str, Any]) -> AsyncIterator[dict]:
        message = clean(req.get("message", ""), self.s.lunex_max_message_chars)
        if not message:
            yield {"type": "error", "message": "Send me a message first."}
            return
        ctx_msgs = (req.get("context") or {}).get("messages") or []
        intent: Intent = detect(message, req.get("skill"), has_chat=bool(ctx_msgs), has_urls=bool(find_urls(message)))

        if intent.skill == "intro":
            for e in self._say(persona.INTRO, "intro"): yield e
        elif intent.skill == "help":
            for e in self._say(persona.HELP, "help"): yield e
        elif intent.skill == "time":
            for e in self._say(time_answer(intent.arg, req.get("tz")), "time"): yield e
        elif intent.skill == "calc":
            try:
                text = f"{intent.arg.strip().rstrip('=?')} = {calculate(intent.arg)}"
            except CalcError as e:
                text = str(e)
            for e in self._say(text, "calc"): yield e
        elif intent.skill == "research":
            async for e in self._research(req, intent.arg or message): yield e
        elif intent.skill == "summarize":
            async for e in self._summarize(req, intent.arg, ctx_msgs): yield e
        elif intent.skill == "faq":
            async for e in self._faq(req, intent.arg or message): yield e
        elif intent.skill == "translate":
            extra = ("The user wants a translation. Work out the target language and the text from their request. "
                     "Reply with the translation only, followed by at most one short note if something is ambiguous or informal.")
            async for e in self._llm(self._messages(req, extra, message, keep=0), temperature=0.2, skill="translate"): yield e
        else:
            async for e in self._chat(req, message): yield e

    # ---------- skills ----------
    async def _chat(self, req, message):
        hits = self.kb.relevant(message)
        extra, sources = "", []
        if hits:
            docs = "\n\n".join(f"[{h.title}]\n{h.text}" for h in hits)
            extra = (f"Help guide for {self.s.lunex_app_name} (use it ONLY if the user is asking about the app; otherwise ignore it. "
                     f"Never invent app features that are not listed here):\n{docs}")
            sources = [{"title": f"Help: {h.title}"} for h in hits[:2]]
        async for e in self._llm(self._messages(req, extra, message), temperature=0.6, skill="chat", sources=sources): yield e

    async def _faq(self, req, question):
        hits = self.kb.search(question, 3)
        if not hits:
            for e in self._say(f"I couldn't find that in the {self.s.lunex_app_name} help guide. "
                               f"For anything else, please contact {self._contact()}.", "faq"): yield e
            return
        docs = "\n\n".join(f"[{h.title}]\n{h.text}" for h in hits)
        extra = (f"Answer the user's question about {self.s.lunex_app_name} using ONLY this help guide. If it does not contain the answer, "
                 f"say you're not sure and suggest contacting {self._contact()}. Give steps as short numbered lines.\n\n{docs}")
        sources = [{"title": f"Help: {h.title}"} for h in hits[:2]]
        async for e in self._llm(self._messages(req, extra, question, keep=4), temperature=0.2, skill="faq", sources=sources): yield e

    async def _research(self, req, query):
        yield {"type": "status", "text": "Searching the web…"}
        query = clean(query, 300)
        try:
            sources = await research.gather_sources(query, self.s.lunex_research_pages, self.search_fn, self.fetch_fn)
        except Exception:
            sources = []
        if not sources:
            for e in self._say("I couldn't get web results right now. Please try again in a moment, or ask me without /research "
                               "and I'll answer from what I already know (it may be out of date).", "research"): yield e
            return
        yield {"type": "status", "text": f"Reading {len(sources)} sources…"}
        user = research.build_user_message(query, sources)
        meta = [{"title": s.title, "url": s.url} for s in sources]
        async for e in self._llm(self._messages(req, "", user, keep=4), temperature=0.3, skill="research", sources=meta): yield e

    async def _summarize(self, req, arg, ctx_msgs):
        urls = find_urls(arg)
        if urls:
            yield {"type": "status", "text": "Reading the link…"}
            try:
                page = await self.fetch_fn(urls[0])
            except UnsafeURL as e:
                for ev in self._say(f"I couldn't open that link: {e}", "summarize"): yield ev
                return
            except Exception:
                for ev in self._say("I couldn't open that link. It may be down or blocked.", "summarize"): yield ev
                return
            if len(page.text) < 120:
                for ev in self._say("That page doesn't have enough readable text for me to summarize.", "summarize"): yield ev
                return
            async for e in self._llm(self._messages(req, "", summarize.text_prompt(page.text, page.title), keep=0), temperature=0.2,
                                     skill="summarize", sources=[{"title": page.title, "url": page.url}]): yield e
            return
        body = re.sub(r"(?i)^\s*(please\s+)?(summari[sz]e|summary of|tl;?dr|recap|sum up)( this| it| the following)?[:\s-]*", "", arg).strip()
        if ctx_msgs and len(body) < 200:
            text, n = summarize.transcript(ctx_msgs)
            if n:
                async for e in self._llm(self._messages(req, "", summarize.chat_prompt(text, n, body), keep=0), temperature=0.2, skill="summarize"): yield e
                return
        if len(body) >= 120:
            async for e in self._llm(self._messages(req, "", summarize.text_prompt(body), keep=0), temperature=0.2, skill="summarize"): yield e
            return
        for e in self._say("Paste the text you want summarized (or a link) after /summarize. "
                           "To summarize a chat, open it and use \"Summarize this chat\".", "summarize"): yield e
