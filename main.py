"""ForNote — upload a heavy medical book (PDF), get AI study notes per chapter.
Run:  python main.py   →  http://127.0.0.1:8000
"""
import os
import shutil
import uuid

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import book_engine
import ai

app = FastAPI(title="ForNote — Notes from Books")

BOOKS: dict[str, dict] = {}   # book_id -> {"title", "chunks", "index"}
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@app.get("/")
def home():
    return FileResponse("static/index.html")


@app.post("/upload")
async def upload(file: UploadFile = File(...)):
    bid = uuid.uuid4().hex[:10]
    path = os.path.join(UPLOAD_DIR, f"{bid}.pdf")
    with open(path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    pages = book_engine.extract_pages(path)
    pages = [p for p in pages if p.strip()]
    if not pages:
        return JSONResponse({"error": "No text could be extracted (scanned PDF?)"},
                            status_code=400)
    chunks = book_engine.make_chunks(pages)
    BOOKS[bid] = {
        "title": file.filename,
        "chunks": chunks,
        "index": book_engine.SearchIndex(chunks),
    }
    return {
        "book_id": bid,
        "title": file.filename,
        "pages": len(pages),
        "chapters": [{"index": c.index, "title": c.title,
                      "pages": f"{c.page_start}-{c.page_end}",
                      "chars": len(c.text)} for c in chunks],
    }


@app.post("/notes")
def notes(book_id: str = Form(...), chapter: int = Form(...),
          lang: str = Form("فارسی")):
    book = BOOKS.get(book_id)
    if not book:
        return JSONResponse({"error": "unknown book_id"}, status_code=404)
    chunk = book["chunks"][chapter]
    mode, text = ai.generate_notes(chunk, lang)
    return {"mode": mode, "title": chunk.title, "notes": text}


@app.post("/ask")
def ask(book_id: str = Form(...), question: str = Form(...)):
    book = BOOKS.get(book_id)
    if not book:
        return JSONResponse({"error": "unknown book_id"}, status_code=404)
    hits = book["index"].search(question, top=3)
    context = "\n\n".join(book["chunks"][i].text for i, _ in hits)
    answer = ai.answer_question(question, context)
    sources = [{"chapter": book["chunks"][i].title, "score": round(s, 3)}
               for i, s in hits]
    return {"answer": answer, "sources": sources}


app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    print("ForNote running → http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
