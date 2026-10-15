"""Decides what the user wants: a /command, or a normal sentence that implies one."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from lunex.bot.calc import LOOKS_LIKE_MATH

SKILLS = ("chat", "research", "summarize", "faq", "translate", "calc", "time", "help")
ALIASES = {"search": "research", "lookup": "research", "summary": "summarize", "tldr": "summarize", "recap": "summarize",
           "ask": "chat", "start": "help", "about": "help", "commands": "help", "translate": "translate", "tr": "translate",
           "calculate": "calc", "math": "calc", "clock": "time", "help": "help", "faq": "faq", "research": "research",
           "summarize": "summarize", "calc": "calc", "time": "time", "chat": "chat"}

GREETING = re.compile(r"^(hi|hello|hey|heya|hiya|yo|sup|howzit|sawubona|molo|good (morning|afternoon|evening)|what can you do\??|who are you\??|what are you\??)[!. ]*$", re.I)
RESEARCH_VERB = re.compile(r"^(please\s+)?(research|look\s?up|search( for| the web for| online for)?|google|find out( about)?)\b[:,\s]*", re.I)
NEEDS_LIVE_INFO = re.compile(
    r"\b(latest|breaking|news|current(ly)?|right now|today'?s|this week|this month|trending|stock price|share price|exchange rate|"
    r"weather|forecast|who won|final score|election results?|release date|price of)\b", re.I)
SUMMARY_WORDS = re.compile(r"\b(summar(ize|ise|y)|tl;?dr|recap|sum up)\b", re.I)
TRANSLATE_WORDS = re.compile(r"^\s*translate\b|\btranslate\b.*\b(to|into)\b|\bhow (do|would) (you|i) say\b.*\b(in|into)\b", re.I)

CITIES = {
    "utc": "UTC", "gmt": "UTC", "south africa": "Africa/Johannesburg", "johannesburg": "Africa/Johannesburg", "durban": "Africa/Johannesburg",
    "cape town": "Africa/Johannesburg", "pretoria": "Africa/Johannesburg", "lagos": "Africa/Lagos", "nigeria": "Africa/Lagos",
    "nairobi": "Africa/Nairobi", "kenya": "Africa/Nairobi", "cairo": "Africa/Cairo", "egypt": "Africa/Cairo", "accra": "Africa/Accra",
    "london": "Europe/London", "uk": "Europe/London", "paris": "Europe/Paris", "berlin": "Europe/Berlin", "moscow": "Europe/Moscow",
    "dubai": "Asia/Dubai", "mumbai": "Asia/Kolkata", "india": "Asia/Kolkata", "delhi": "Asia/Kolkata", "singapore": "Asia/Singapore",
    "beijing": "Asia/Shanghai", "china": "Asia/Shanghai", "tokyo": "Asia/Tokyo", "japan": "Asia/Tokyo", "sydney": "Australia/Sydney",
    "new york": "America/New_York", "los angeles": "America/Los_Angeles", "chicago": "America/Chicago", "toronto": "America/Toronto",
    "sao paulo": "America/Sao_Paulo", "brazil": "America/Sao_Paulo",
}


@dataclass
class Intent:
    skill: str
    arg: str


def valid_tz(name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(name) if name else ZoneInfo("UTC")
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return ZoneInfo("UTC")


def time_answer(arg: str, tz_name: str | None) -> str:
    key = arg.strip().lower().removeprefix("in ").removeprefix("the time in ").strip(" ?.!")
    if not key:
        tz = valid_tz(tz_name)
        label = "your time zone" if tz_name else "UTC"
    elif key in CITIES:
        tz, label = ZoneInfo(CITIES[key]), arg.strip().strip("?.! ").title()
    else:
        try:
            tz, label = ZoneInfo(arg.strip().replace(" ", "_")), arg.strip()
        except (ZoneInfoNotFoundError, ValueError, OSError):
            return "I don't know that place yet. Try a big city or country, like /time London, or a zone like Africa/Johannesburg."
    now = datetime.now(tz)
    return f"It's {now.strftime('%H:%M on %A, %d %B %Y')} in {label}."


def detect(message: str, forced: str | None = None, has_chat: bool = False, has_urls: bool = False) -> Intent:
    m = message.strip()
    if forced and forced != "auto":
        return Intent(forced, re.sub(r"^/\w+\s*", "", m) if m.startswith("/") else m)
    if m.startswith("/"):
        word, _, rest = m[1:].partition(" ")
        skill = ALIASES.get(word.lower().split("@")[0])
        if skill:
            return Intent(skill, rest.strip())
        return Intent("help", "")           # unknown command -> show the list
    if GREETING.match(m):
        return Intent("intro", "")
    if LOOKS_LIKE_MATH.match(m) and re.search(r"\d", m) and re.search(r"[+\-*/^x×÷%]", m[1:]):
        return Intent("calc", m)
    if RESEARCH_VERB.match(m):
        return Intent("research", RESEARCH_VERB.sub("", m, count=1).strip() or m)
    if SUMMARY_WORDS.search(m) and (has_chat or has_urls or len(m) > 300):
        return Intent("summarize", m)
    if TRANSLATE_WORDS.search(m):
        return Intent("translate", m)
    if NEEDS_LIVE_INFO.search(m) and "?" in m or NEEDS_LIVE_INFO.search(m) and len(m.split()) >= 4:
        return Intent("research", m)
    return Intent("chat", m)
