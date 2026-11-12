"""Notes generation: Google Gemini (free API key) with automatic offline fallback."""
import os
import json

import book_engine

# Free API key from https://aistudio.google.com/apikey  (free tier, no credit card)
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL = "gemini-2.0-flash"

PROMPT = """You are an expert medical study-note writer.
Below is a section of a textbook (may be a heavy medical book).
Write study notes in {lang} with EXACTLY these markdown sections:

## خلاصه / Summary
4-8 concise sentences covering the core of the section.

## مفاهیم کلیدی / Key Concepts
Bullet list of the most important concepts with one-line explanations.

## اصطلاحات / Terms & Definitions
Bullet list: **term** — short definition.

## نکات امتحانی / Exam Pearls
3-6 bullets of facts likely to be tested.

TEXT:
---
{text}
---
"""


def _gemini_notes(text: str, lang: str) -> str:
    from google import genai
    client = genai.Client(api_key=GEMINI_KEY)
    resp = client.models.generate_content(
        model=MODEL,
        contents=PROMPT.format(lang=lang, text=text[:120_000]),
    )
    return resp.text


def _offline_notes(chunk: "book_engine.Chunk", lang: str) -> str:
    summary = book_engine.offline_summary(chunk.text)
    terms = book_engine.offline_keyterms(chunk.text)
    lines = [f"## خلاصه (آفلاین) / Summary\n", summary, "\n## اصطلاحات پرتکرار / Frequent Terms\n"]
    lines += [f"- **{t}**" for t in terms]
    lines.append("\n_(حالت آفلاین: خلاصه‌سازی استخراجی بدون مدل — برای یادداشت‌های هوشمند، کلید رایگان Gemini را در README تنظیم کنید)_")
    return "\n".join(lines)


def generate_notes(chunk: "book_engine.Chunk", lang: str = "فارسی") -> tuple[str, str]:
    """Returns (mode, notes_markdown). mode is 'gemini' or 'offline'."""
    if GEMINI_KEY:
        try:
            return "gemini", _gemini_notes(chunk.text, lang)
        except Exception as e:
            fallback = _offline_notes(chunk, lang)
            return "offline", f"> ⚠️ Gemini error: {e}\n\n" + fallback
    return "offline", _offline_notes(chunk, lang)


def answer_question(question: str, context: str) -> str:
    if not GEMINI_KEY:
        return "برای پاسخ هوشمند به سؤالات، کلید رایگان Gemini API لازم است (README را ببینید). " \
               "در حالت آفلاین فقط جست‌وجو در متن کتاب فعال است."
    from google import genai
    client = genai.Client(api_key=GEMINI_KEY)
    resp = client.models.generate_content(
        model=MODEL,
        contents=f"Answer the question using ONLY the textbook context. "
                 f"Answer in the same language as the question.\n\n"
                 f"CONTEXT:\n{context[:120_000]}\n\nQUESTION: {question}",
    )
    return resp.text
