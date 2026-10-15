"""Web search without any API key: the `ddgs` package, with a plain DuckDuckGo HTML page as backup."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from urllib.parse import parse_qs, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger("lunex.search")


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


def _ddgs_search(query: str, n: int) -> list[SearchResult]:
    from ddgs import DDGS                           # imported here so a missing/broken package never stops LUNEX starting
    rows = DDGS(timeout=8).text(query, max_results=n, safesearch="moderate")
    return [SearchResult((r.get("title") or "")[:200], r.get("href") or r.get("url") or "", (r.get("body") or "")[:400])
            for r in rows or [] if (r.get("href") or r.get("url"))]


async def _html_search(query: str, n: int) -> list[SearchResult]:
    async with httpx.AsyncClient(timeout=8, trust_env=False, headers={"User-Agent": "Mozilla/5.0 (compatible; LUNEX-assistant/0.2)"}) as c:
        r = await c.post("https://html.duckduckgo.com/html/", data={"q": query})
    soup = BeautifulSoup(r.text, "html.parser")
    out: list[SearchResult] = []
    for item in soup.select("div.result"):
        a = item.select_one("a.result__a")
        if not a or not a.get("href"):
            continue
        href = a["href"]
        q = parse_qs(urlparse(href).query)
        if "uddg" in q:
            href = unquote(q["uddg"][0])
        sn = item.select_one(".result__snippet")
        out.append(SearchResult(a.get_text(" ", strip=True)[:200], href, sn.get_text(" ", strip=True)[:400] if sn else ""))
        if len(out) >= n:
            break
    return out


async def web_search(query: str, n: int = 6) -> list[SearchResult]:
    """Never raises: an empty list means 'nothing found / search unavailable'."""
    try:
        res = await asyncio.wait_for(asyncio.to_thread(_ddgs_search, query, n), timeout=12)
        if res:
            return res
    except Exception as e:                          # network, rate limit, package problems...
        log.info("ddgs failed: %s", type(e).__name__)
    try:
        return await _html_search(query, n)
    except Exception as e:
        log.info("html search failed: %s", type(e).__name__)
        return []
