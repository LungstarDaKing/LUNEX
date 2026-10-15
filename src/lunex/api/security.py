"""Who may talk to LUNEX, and how much. Protects your free AI quotas from abuse."""
from __future__ import annotations

import hashlib
import hmac
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException, Request

from lunex.config import Settings


@dataclass
class User:
    id: str


class Authenticator:
    """Accepts the same login token the LSDKChat app already has (checked with Supabase), or a server token."""

    def __init__(self, s: Settings, client: httpx.AsyncClient | None = None):
        self.s, self.client = s, client or httpx.AsyncClient(timeout=6)
        self._cache: dict[str, tuple[str, float]] = {}

    async def __call__(self, request: Request) -> User:
        s = self.s
        if s.lunex_auth == "off" and s.is_dev:
            return User("dev")
        header = request.headers.get("authorization", "")
        token = header[7:].strip() if header.lower().startswith("bearer ") else ""
        if not token:
            raise HTTPException(401, "Please sign in to use LUNEX.")
        if s.lunex_api_token and hmac.compare_digest(token, s.lunex_api_token):
            return User("svc:" + request.headers.get("x-lunex-user", "service")[:64])
        if not (s.supabase_url and s.supabase_anon_key):
            raise HTTPException(503, "LUNEX sign-in is not configured.")
        key = hashlib.sha256(token.encode()).hexdigest()
        hit = self._cache.get(key)
        if hit and hit[1] > time.monotonic():
            return User(hit[0])
        try:
            r = await self.client.get(s.supabase_url.rstrip("/") + "/auth/v1/user",
                                      headers={"apikey": s.supabase_anon_key, "Authorization": f"Bearer {token}"})
        except httpx.HTTPError:
            raise HTTPException(503, "Sign-in check is unavailable. Try again shortly.")
        if r.status_code != 200 or not r.json().get("id"):
            raise HTTPException(401, "Your session has expired. Please sign in again.")
        uid = str(r.json()["id"])
        if len(self._cache) > 5000:
            self._cache.clear()
        self._cache[key] = (uid, time.monotonic() + 60)
        return User(uid)


class Limiter:
    """Per-minute and per-day limits for each person, a daily cap for everyone, and no pile-ups."""

    def __init__(self, s: Settings):
        self.s = s
        self.minute: dict[str, deque] = defaultdict(deque)
        self.day: dict[tuple[str, str], int] = defaultdict(int)
        self.global_day: dict[str, int] = defaultdict(int)
        self.busy: dict[str, int] = defaultdict(int)

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def remaining(self, uid: str) -> int:
        return max(self.s.lunex_user_per_day - self.day[(uid, self._today())], 0)

    def start(self, uid: str) -> None:
        now, today = time.monotonic(), self._today()
        q = self.minute[uid]
        while q and now - q[0] > 60:
            q.popleft()
        if self.busy[uid] >= 2:
            raise HTTPException(429, "One moment - I'm still answering your last message.", headers={"Retry-After": "5"})
        if len(q) >= self.s.lunex_user_per_minute:
            raise HTTPException(429, "You're sending messages too fast. Wait a few seconds.", headers={"Retry-After": str(int(60 - (now - q[0])) + 1)})
        if self.day[(uid, today)] >= self.s.lunex_user_per_day:
            raise HTTPException(429, "You've used all your LUNEX messages for today. They reset at midnight UTC.", headers={"Retry-After": "3600"})
        if self.global_day[today] >= self.s.lunex_global_per_day:
            raise HTTPException(429, "LUNEX is very busy today. Please try again tomorrow.", headers={"Retry-After": "3600"})
        q.append(now); self.day[(uid, today)] += 1; self.global_day[today] += 1; self.busy[uid] += 1
        for k in [k for k in self.day if k[1] != today]:      # forget yesterday
            del self.day[k]
        for k in [k for k in self.global_day if k != today]:
            del self.global_day[k]

    def finish(self, uid: str) -> None:
        self.busy[uid] = max(self.busy[uid] - 1, 0)
