"""Small, dependency-free search over the app's help documents (BM25).

Add more .md files (set LUNEX_KNOWLEDGE_DIR) and LUNEX can answer from them too. Each "## heading"
section is one searchable chunk.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

STOP = set("""a an the and or but if then so of to in on at by for with from as is are was were be been being am do does did
have has had i you he she it we they me my your our their this that these those what which who how can could should would will
may might must not no yes please about into out up down over under again also just very more most some any each other such
there here when where why than too s t""".split())


def stem(w: str) -> str:
    """Very light stemming so "ringtones", "ringtone", "called" and "calling" match their root word."""
    if w.endswith("ies") and len(w) > 4:
        w = w[:-3] + "y"
    elif w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        w = w[:-1]
    for suf in ("ing", "ion", "ed"):
        if w.endswith(suf) and len(w) - len(suf) >= 4:
            return w[: -len(suf)]
    return w


def tokens(text: str) -> list[str]:
    return [stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1]


@dataclass
class Chunk:
    title: str
    text: str
    toks: list[str]


@dataclass
class Hit:
    title: str
    text: str
    score: float
    matched: int
    title_hit: bool = False


class KnowledgeBase:
    def __init__(self, extra_dir: str = ""):
        self.chunks: list[Chunk] = []
        base = resources.files("lunex") / "knowledge"
        for f in sorted(base.iterdir(), key=lambda p: p.name):
            if f.name.endswith(".md"):
                self._add(f.read_text(encoding="utf-8"))
        if extra_dir and Path(extra_dir).is_dir():
            for f in sorted(Path(extra_dir).glob("*.md")):
                self._add(f.read_text(encoding="utf-8"))
        n = max(len(self.chunks), 1)
        self.avg = sum(len(c.toks) for c in self.chunks) / n
        df: dict[str, int] = {}
        for c in self.chunks:
            for t in set(c.toks):
                df[t] = df.get(t, 0) + 1
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def _add(self, md: str) -> None:
        for block in re.split(r"(?m)^## ", md)[1:]:
            title, _, body = block.partition("\n")
            body = body.strip()
            if body:
                # the heading counts double: it is the best summary of the chunk
                self.chunks.append(Chunk(title.strip(), body, tokens(title) * 2 + tokens(body)))

    def search(self, query: str, k: int = 3) -> list[Hit]:
        q = set(tokens(query))
        hits: list[Hit] = []
        for c in self.chunks:
            tf: dict[str, int] = {}
            for t in c.toks:
                tf[t] = tf.get(t, 0) + 1
            score, matched = 0.0, 0
            for t in q:
                f = tf.get(t, 0)
                if f:
                    matched += 1
                    score += self.idf.get(t, 0) * (f * 2.5) / (f + 1.5 * (0.25 + 0.75 * len(c.toks) / (self.avg or 1)))
            if score > 0:
                hits.append(Hit(c.title, c.text, score, matched, bool(q & set(tokens(c.title)))))
        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:k]

    def relevant(self, query: str, k: int = 3, min_score: float = 3.0, min_matched: int = 2) -> list[Hit]:
        """Hits strong enough to be worth showing to the AI as help text."""
        hits = self.search(query, k)
        return [h for h in hits if (h.matched >= min_matched and h.score >= min_score) or (h.title_hit and h.score >= 3.0)]
