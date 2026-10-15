"""Safe web page fetching for the research and summarize skills.

LUNEX downloads pages on behalf of users, so this must never be usable to reach private
addresses (the server's own network, cloud metadata services, localhost...). Every address a
page name resolves to - including after each redirect - must be a public internet address.
"""
from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

MAX_BYTES = 1_500_000
MAX_REDIRECTS = 3
USER_AGENT = "Mozilla/5.0 (compatible; LUNEX-assistant/0.2)"
_URL_RE = re.compile(r"https?://[^\s<>\"')\]]+", re.I)


class UnsafeURL(Exception):
    pass


@dataclass
class Page:
    url: str
    title: str
    text: str


def find_urls(text: str) -> list[str]:
    return [u.rstrip(".,;:!?") for u in _URL_RE.findall(text or "")]


async def check_public(url: str) -> None:
    """Raise UnsafeURL unless the URL is plain http(s) to a public address on a normal port."""
    p = urlparse(url)
    if p.scheme not in ("http", "https") or not p.hostname:
        raise UnsafeURL("Only http and https links are allowed.")
    if p.username or p.password:
        raise UnsafeURL("Links with a login are not allowed.")
    port = p.port or (443 if p.scheme == "https" else 80)
    if port not in (80, 443, 8080, 8443):
        raise UnsafeURL("That port is not allowed.")
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(p.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise UnsafeURL("That address could not be found.") from e
    if not infos:
        raise UnsafeURL("That address could not be found.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:                      # private, loopback, link-local, carrier-grade NAT, reserved...
            raise UnsafeURL("That address is not on the public internet.")


def extract(html: str, url: str, max_chars: int = 6000) -> Page:
    soup = BeautifulSoup(html, "html.parser")
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form", "svg", "iframe", "button"]):
        tag.decompose()
    root = soup.find("article") or soup.find("main") or soup.body or soup
    parts = [t.get_text(" ", strip=True) for t in root.find_all(["h1", "h2", "h3", "p", "li"])]
    text = "\n".join(p for p in parts if len(p) > 25) or root.get_text(" ", strip=True)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text).strip()
    return Page(url=url, title=title[:200] or urlparse(url).hostname or url, text=text[:max_chars])


async def fetch_page(url: str, *, timeout: float = 7.0, max_chars: int = 6000, client: httpx.AsyncClient | None = None) -> Page:
    own = client is None
    client = client or httpx.AsyncClient(follow_redirects=False, timeout=timeout, headers={"User-Agent": USER_AGENT}, trust_env=False)
    try:
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            await check_public(current)
            async with client.stream("GET", current, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"}) as r:
                if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                    current = urljoin(current, r.headers["location"])
                    continue
                if r.status_code >= 400:
                    raise UnsafeURL(f"The page answered with an error ({r.status_code}).")
                ctype = r.headers.get("content-type", "").lower()
                if ctype and not any(t in ctype for t in ("text/html", "text/plain", "application/xhtml")):
                    raise UnsafeURL("That link is not a web page I can read.")
                body = b""
                async for chunk in r.aiter_bytes():
                    body += chunk
                    if len(body) > MAX_BYTES:
                        break
                enc = r.encoding or "utf-8"
                text = body[:MAX_BYTES].decode(enc, errors="replace")
                if "text/plain" in ctype:
                    return Page(current, urlparse(current).hostname or current, re.sub(r"\s+", " ", text)[:max_chars])
                return extract(text, current, max_chars)
        raise UnsafeURL("Too many redirects.")
    finally:
        if own:
            await client.aclose()
