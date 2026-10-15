import json

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from lunex.ai.providers.base import AIProvider, ProviderError
from lunex.ai.providers.capabilities import ProviderCapabilities
from lunex.ai.router import ProviderRouter
from lunex.config import Settings


class FakeProvider(AIProvider):
    """Echoes what it was given so tests can inspect the prompts LUNEX built."""
    def __init__(self, name="fake", fail=None, reply="OK-REPLY"):
        super().__init__(name, {})
        self.fail, self.reply, self.calls = fail, reply, []

    def _detect_capabilities(self):
        return ProviderCapabilities.TEXT

    async def chat(self, messages, options=None):
        self.calls.append(messages)
        if self.fail: raise ProviderError(self.provider_name, "down", rate_limited=self.fail == "rate")
        return self.reply

    async def chat_stream(self, messages, options=None):
        self.calls.append(messages)
        if self.fail: raise ProviderError(self.provider_name, "down", rate_limited=self.fail == "rate")
        for w in self.reply.split(" "):
            yield w + " "


def settings(**kw):
    base = dict(lunex_env="development", lunex_auth="off", lunex_providers="", _env_file=None)
    base.update(kw)
    return Settings(**base)


@pytest.fixture
def fake():
    return FakeProvider()


def fake_openai_app(log):
    """A tiny server that speaks the OpenAI chat API, so the real OpenAI client code is tested."""
    app = FastAPI()

    @app.post("/v1/chat/completions")
    async def comp(req: Request):
        body = await req.json(); log.append(body)
        if body["messages"][-1]["content"] == "boom":
            return JSONResponse({"error": {"message": "rate"}}, status_code=429)
        if body.get("stream"):
            async def gen():
                for w in ["Hel", "lo ", "there"]:
                    yield "data: " + json.dumps({"id": "1", "object": "chat.completion.chunk", "created": 1, "model": "m",
                                                  "choices": [{"index": 0, "delta": {"content": w}, "finish_reason": None}]}) + "\n\n"
                yield "data: [DONE]\n\n"
            return StreamingResponse(gen(), media_type="text/event-stream")
        return {"id": "1", "object": "chat.completion", "created": 1, "model": "m",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello there"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}
    return app
