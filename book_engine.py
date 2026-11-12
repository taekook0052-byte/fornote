"""PDF extraction, chapter-based chunking, and offline (no-model) summarization."""
import re
from dataclasses import dataclass, field
from math import log, sqrt

from pypdf import PdfReader


# ---------------------------------------------------------------- extraction

def extract_pages(path: str) -> list[str]:
    reader = PdfReader(path)
    pages = []
    for p in reader.pages:
        try:
            t = p.extract_text() or ""
        except Exception:
            t = ""
        pages.append(t)
    return pages


def clean_text(t: str) -> str:
    t = t.replace("\u00ad", "")          # soft hyphen
    t = re.sub(r"-\n(?=[a-z])", "", t)   # de-hyphenate line breaks
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


# ---------------------------------------------------------------- chunking

@dataclass
class Chunk:
    index: int
    title: str
    text: str
    page_start: int
    page_end: int


CHAPTER_RE = re.compile(
    r"^\s*(chapter|ch\.)\s+\d+|^\s*\d{1,2}\s+[A-Z][^.]{3,60}$|"
    r"^\s*(part|section|فصل|بخش)\s*\d*",
    re.IGNORECASE,
)


def make_chunks(pages: list[str], target_chars: int = 6000) -> list[Chunk]:
    """Group pages into chapter-like chunks. Splits on 'Chapter N'-style
    headings, otherwise on target_chars size."""
    chunks: list[Chunk] = []
    cur: list[str] = []
    cur_title = "Beginning of book"
    cur_start = 1
    cur_len = 0
    for i, page in enumerate(pages, start=1):
        first_lines = page.strip().splitlines()[:3]
        heading = next((l.strip() for l in first_lines if CHAPTER_RE.match(l)), None)
        if heading and cur_len > target_chars // 2:
            chunks.append(Chunk(len(chunks), cur_title, clean_text("\n".join(cur)),
                                cur_start, i - 1))
            cur, cur_title, cur_start, cur_len = [], heading or cur_title, i, 0
        if heading and not cur:
            cur_title = heading
        cur.append(page)
        cur_len += len(page)
        if cur_len >= target_chars * 2:
            chunks.append(Chunk(len(chunks), cur_title, clean_text("\n".join(cur)),
                                cur_start, i))
            cur, cur_title, cur_start, cur_len = [], "Continuation", i + 1, 0
    if cur:
        chunks.append(Chunk(len(chunks), cur_title, clean_text("\n".join(cur)),
                            cur_start, len(pages)))
    return chunks


# ------------------------------------------------- offline (no-model) notes

STOP = set("""a an the and or but of in on at to for with from by as is are was were be
been being this that these those it its if then than so such not no can could may might
will would shall should have has had do does did we you they he she i our your their
about into over under between within without also more most other some any each which
who whom when where what how why all both few many much very using use used""".split())


def _sentences(text: str) -> list[str]:
    s = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\u0600-\u06FF])", text)
    return [x.strip() for x in s if 40 < len(x.strip()) < 600]


def _word_freqs(text: str) -> dict[str, float]:
    freqs: dict[str, int] = {}
    for w in re.findall(r"[A-Za-z\u0600-\u06FF]{3,}", text.lower()):
        if w not in STOP:
            freqs[w] = freqs.get(w, 0) + 1
    if not freqs:
        return {}
    m = max(freqs.values())
    return {w: f / m for w, f in freqs.items()}


def offline_summary(text: str, max_sents: int = 12) -> str:
    """Extractive summarization: score sentences by term-frequency signal.
    Works with zero models, zero downloads, fully offline."""
    freqs = _word_freqs(text)
    if not freqs:
        return ""
    sents = _sentences(text)
    scored = []
    for i, s in enumerate(sents):
        ws = re.findall(r"[A-Za-z\u0600-\u06FF]{3,}", s.lower())
        score = sum(freqs.get(w, 0) for w in ws) / (len(ws) + 1)
        scored.append((score, i, s))
    top = sorted(sorted(scored, reverse=True)[:max_sents], key=lambda x: x[1])
    return "\n\n".join(s for _, _, s in top)


def offline_keyterms(text: str, k: int = 20) -> list[str]:
    freqs = _word_freqs(text)
    return sorted(freqs, key=freqs.get, reverse=True)[:k]


# ------------------------------------------------------- TF-IDF search index

class SearchIndex:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self.docs = [c.text for c in chunks]
        self.vocab: dict[str, int] = {}
        self.tfidf: list[dict[int, float]] = []
        self._build()

    def _vec(self, text: str) -> dict[int, float]:
        v: dict[int, float] = {}
        for w in re.findall(r"[a-z\u0600-\u06FF]{3,}", text.lower()):
            if w in STOP:
                continue
            j = self.vocab.setdefault(w, len(self.vocab))
            v[j] = v.get(j, 0) + 1
        return v

    def _build(self):
        N = max(len(self.docs), 1)
        raw = [self._vec(d) for d in self.docs]
        df: dict[int, int] = {}
        for v in raw:
            for j in v:
                df[j] = df.get(j, 0) + 1
        self.idf = {j: log(N / (df[j])) + 1 for j in df}
        for v in raw:
            tv = {j: (1 + log(f)) * self.idf[j] for j, f in v.items() if j in self.idf}
            norm = sqrt(sum(x * x for x in tv.values())) or 1.0
            self.tfidf.append({j: x / norm for j, x in tv.items()})

    def search(self, query: str, top: int = 5) -> list[tuple[int, float]]:
        q = self._vec(query)
        qv = {j: (1 + log(f)) * self.idf.get(j, 0) for j, f in q.items()}
        norm = sqrt(sum(x * x for x in qv.values())) or 1.0
        qv = {j: x / norm for j, x in qv.items()}
        scores = []
        for i, dv in enumerate(self.tfidf):
            s = sum(f * dv[j] for j, f in qv.items() if j in dv)
            scores.append((i, s))
        return sorted(scores, key=lambda x: -x[1])[:top]
