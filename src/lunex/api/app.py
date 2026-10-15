"""The LUNEX web service.   Run:  uvicorn lunex.api.app:app --port 8000"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse

from lunex import __version__
from lunex.ai.registry import build_router
from lunex.api.schemas import ChatRequest, ChatResponse
from lunex.api.security import Authenticator, Limiter, User
from lunex.bot.core import LunexBot
from lunex.config import Settings, get_settings

log = logging.getLogger("lunex")
MAX_BODY = 200_000

SUGGESTIONS = ["How do I make a group call?", "/research best free VPN for students", "/summarize", "/translate zulu: good morning", "/calc 15% of 240"]


def create_app(settings: Optional[Settings] = None, bot: Optional[LunexBot] = None, auth: Optional[Authenticator] = None) -> FastAPI:
    s = settings or get_settings()
    app = FastAPI(title="LUNEX", version=__version__, docs_url="/docs" if s.is_dev else None, redoc_url=None, openapi_url="/openapi.json" if s.is_dev else None)
    bot = bot or LunexBot(build_router(s), s)
    authenticate = auth or Authenticator(s)
    limiter = Limiter(s)

    app.add_middleware(CORSMiddleware, allow_origins=s.origins, allow_methods=["GET", "POST", "OPTIONS"],
                       allow_headers=["Authorization", "Content-Type", "X-Lunex-User"], max_age=600)

    @app.middleware("http")
    async def guard(request: Request, call_next):
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY:
            return JSONResponse({"detail": "That message is too large."}, status_code=413)
        resp = await call_next(request)
        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Cache-Control"] = "no-store"
        return resp

    async def user(request: Request) -> User:
        return await authenticate(request)

    @app.get("/health")
    async def health():
        return {"ok": True, "version": __version__, "ai_ready": bot.router.available}

    @app.get("/v1/skills")
    async def skills(_: User = Depends(user)):
        return {"name": "LUNEX", "version": __version__, "suggestions": SUGGESTIONS,
                "commands": ["/help", "/research", "/summarize", "/faq", "/translate", "/calc", "/time"]}

    def _payload(body: ChatRequest) -> dict[str, Any]:
        return body.model_dump()

    @app.post("/v1/chat", response_model=ChatResponse)
    async def chat(body: ChatRequest, u: User = Depends(user)):
        limiter.start(u.id)
        try:
            text, skill, sources = "", "chat", []
            async for ev in bot.respond(_payload(body)):
                if ev["type"] == "delta":
                    text += ev["text"]
                elif ev["type"] == "done":
                    skill, sources = ev["skill"], ev["sources"]
                elif ev["type"] == "error":
                    raise HTTPException(503, ev["message"])
            return ChatResponse(reply=text.strip(), skill=skill, sources=sources, remaining_today=limiter.remaining(u.id))
        finally:
            limiter.finish(u.id)

    @app.post("/v1/chat/stream")
    async def chat_stream(body: ChatRequest, u: User = Depends(user)):
        limiter.start(u.id)
        payload = _payload(body)

        async def gen():
            try:
                async for ev in bot.respond(payload):
                    if ev["type"] == "done":
                        ev = {**ev, "remaining_today": limiter.remaining(u.id)}
                    yield f"event: {ev['type']}\ndata: {json.dumps(ev, ensure_ascii=False)}\n\n"
            except Exception:
                log.exception("stream failed")
                yield 'event: error\ndata: {"type":"error","message":"Something went wrong. Please try again."}\n\n'
            finally:
                limiter.finish(u.id)

        return StreamingResponse(gen(), media_type="text/event-stream", headers={"X-Accel-Buffering": "no"})

    if s.is_dev:
        demo = Path(__file__).resolve().parents[3] / "client" / "demo.html"

        @app.get("/lunex.js")
        async def demo_js():
            return Response((demo.parent / "lunex.js").read_text(encoding="utf-8"), media_type="text/javascript")

        @app.get("/demo", response_class=HTMLResponse)
        async def demo_page():
            return demo.read_text(encoding="utf-8") if demo.exists() else "demo.html not found"

    return app


app = create_app()
