"""Summarize skill helpers: turn a chat transcript / pasted text into a prompt."""
from __future__ import annotations

from typing import Iterable

from lunex.bot.research import neutralize

MAX_CHARS = 14000


def transcript(messages: Iterable[dict], limit: int = 200) -> tuple[str, int]:
    """Plain 'name: text' lines, the newest ones if there are too many. Returns (text, how many messages were used)."""
    lines = []
    for m in list(messages)[-limit:]:
        text = " ".join(str(m.get("text", "")).split())
        if text:
            who = " ".join(str(m.get("author", "Someone")).split())[:40] or "Someone"
            lines.append(f"{who}: {text[:500]}")
    while lines and sum(len(x) + 1 for x in lines) > MAX_CHARS:
        lines.pop(0)
    return "\n".join(lines), len(lines)


def chat_prompt(text: str, count: int, request: str) -> str:
    return (f"The user shared {count} recent messages from one of their chats and asked: {request or 'Summarize this chat.'}\n\n"
            f"<chat>\n{neutralize(text)}\n</chat>\n\n"
            "Summarize for someone who missed it. Plain text. Start with one sentence of overview, then up to 5 lines starting with '- ' for "
            "key points and decisions. If there are tasks or questions still open, add 'To do:' with short '- ' lines (include names). "
            "Don't invent anything that isn't in the messages. If nothing important was said, say so in one sentence.")


def text_prompt(text: str, title: str = "") -> str:
    head = f" (from the page titled '{neutralize(title)}')" if title else ""
    return (f"Summarize the following text{head} for a busy reader.\n\n<untrusted>\n{neutralize(text[:MAX_CHARS])}\n</untrusted>\n\n"
            "Plain text: one sentence of overview, then up to 5 lines starting with '- ' for the key points. "
            "Don't add facts that are not in the text.")
