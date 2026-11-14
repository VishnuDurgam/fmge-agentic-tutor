import hmac
import os

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import llm, retrieval
from . import library
from .agents import flashcards, generate, mock, planner, quiz, tutor
from .config import CORS_ORIGINS, SUBJECTS
from .db import init_db

app = FastAPI(title="FMGE Agentic Tutor API")
ACCESS_CODE = os.getenv("APP_PASSCODE", "")  # set this for a private deployment (only people with the code can use it)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


PRIVATE_CODE = os.getenv("PRIVATE_CODE", "")  # unlocks notes from the private repo (content/raw/private)


@app.middleware("http")
async def private_gate(request: Request, call_next):
    sent = request.headers.get("x-private-code", "")
    retrieval.unlocked.set(bool(PRIVATE_CODE) and hmac.compare_digest(sent.encode(), PRIVATE_CODE.encode()))
    return await call_next(request)


@app.middleware("http")
async def passcode_gate(request: Request, call_next):
    if ACCESS_CODE and request.method != "OPTIONS" and request.url.path not in ("/health", "/docs", "/openapi.json"):
        sent = request.headers.get("x-access-code", "")
        if not hmac.compare_digest(sent.encode(), ACCESS_CODE.encode()):
            return JSONResponse({"detail": "Access code required"}, status_code=401)
    return await call_next(request)


@app.get("/auth/check")
def auth_check():
    return {"ok": True}


@app.on_event("startup")
def _startup():
    init_db()


def learner_id(x_learner_id: str | None) -> str:
    if not x_learner_id or len(x_learner_id) > 64:
        raise HTTPException(400, "X-Learner-Id header required")
    return x_learner_id


class Ask(BaseModel):
    question: str
    subject: str = ""
    source: str = ""


class Submit(BaseModel):
    question_id: str
    choice: int


class Profile(BaseModel):
    exam_date: str
    hours_per_day: float = 4


class CardIn(BaseModel):
    front: str
    back: str
    subject: str = ""


class Review(BaseModel):
    quality: int


class Gen(BaseModel):
    topic: str
    subject: str = ""
    n: int = 5


@app.get("/health")
def health():
    return {"ok": True, "ai": llm.available(), "locked": bool(ACCESS_CODE)}


@app.get("/health/ai")
def health_ai():
    """Tiny live test of the AI keys; shows the provider's own error text when it fails."""
    prov = llm._active()
    if not prov:
        return {"ok": False, "providers": [], "error": "No AI key is set on the server"}
    try:
        return {"ok": True, "providers": prov, "reply": llm.complete("Reply with the single word OK.", "ping", 20)[:60]}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "providers": prov, "error": str(e)[:500]}


def _ai_guard(fn, *a):
    try:
        return fn(*a)
    except HTTPException:
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"The AI service failed: {str(e)[:300]}")


@app.get("/subjects")
def subjects():
    return SUBJECTS


@app.post("/tutor/ask")
def ask(b: Ask, x_learner_id: str | None = Header(None)):
    return _ai_guard(tutor.ask, b.question, b.subject, learner_id(x_learner_id), b.source)


@app.get("/quiz/next")
def next_q(subject: str | None = None, x_learner_id: str | None = Header(None)):
    q = quiz.next_question(learner_id(x_learner_id), subject)
    if not q:
        raise HTTPException(404, "No questions available")
    return q


@app.post("/quiz/submit")
def submit(b: Submit, x_learner_id: str | None = Header(None)):
    r = quiz.submit(learner_id(x_learner_id), b.question_id, b.choice)
    if not r:
        raise HTTPException(404, "Unknown question")
    return r


@app.get("/quiz/stats")
def stats(x_learner_id: str | None = Header(None)):
    return quiz.topic_stats(learner_id(x_learner_id))


@app.put("/planner/profile")
def put_profile(b: Profile, x_learner_id: str | None = Header(None)):
    planner.set_profile(learner_id(x_learner_id), b.exam_date, b.hours_per_day)
    return {"ok": True}


@app.get("/planner/plan")
def plan(x_learner_id: str | None = Header(None)):
    p = planner.build_plan(learner_id(x_learner_id))
    if p is None:
        raise HTTPException(404, "Set your exam date first")
    return p


@app.get("/cards/due")
def cards_due(x_learner_id: str | None = Header(None)):
    return flashcards.due(learner_id(x_learner_id))


@app.post("/cards")
def add_card(b: CardIn, x_learner_id: str | None = Header(None)):
    return {"id": flashcards.add_card(learner_id(x_learner_id), b.front, b.back, b.subject)}


@app.post("/cards/generate")
def gen_cards(b: Gen, x_learner_id: str | None = Header(None)):
    return _ai_guard(generate.cards, learner_id(x_learner_id), b.topic, min(b.n, 10))


class GenQ(BaseModel):
    topic: str = ""
    n: int = 5
    source: str = ""


@app.post("/quiz/generate")
def gen_questions(b: GenQ, x_learner_id: str | None = Header(None)):
    me = learner_id(x_learner_id)
    if not llm.available():
        raise HTTPException(503, "Add a free GEMINI_API_KEY or GROQ_API_KEY (or a local OLLAMA_MODEL) on the server to generate questions")
    return _ai_guard(generate.questions, b.topic or None, min(b.n, 20), b.source or None, me)


@app.get("/library/stats")
def library_stats(x_learner_id: str | None = Header(None)):
    chunks = retrieval.visible(retrieval._index()[0])
    shared = sorted({c["source"] for c in chunks})
    mine = library.source_names(learner_id(x_learner_id))
    return {"chunks": len(chunks), "sources": [{"name": n, "mine": False} for n in shared]
            + [{"name": n, "mine": True} for n in sorted(set(mine))]}


@app.post("/library/upload")
async def library_upload(file: UploadFile = File(...), x_learner_id: str | None = Header(None)):
    me = learner_id(x_learner_id)
    data = await file.read()
    if len(data) > library.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"File is larger than {library.MAX_UPLOAD_MB} MB")
    return {"id": library.ingest_bytes(me, file.filename or "upload", data)}


class LinkIn(BaseModel):
    url: str


@app.post("/library/link")
def library_link(b: LinkIn, x_learner_id: str | None = Header(None)):
    if "drive.google.com/drive/folders" in b.url or "drive.google.com/drive/u/" in b.url and "/folders/" in b.url:
        raise HTTPException(400, "Google Drive folder links are not supported. Open one PDF, tap Share, set Anyone with the link, and paste that file link, or upload the PDF directly.")
    return {"id": library.ingest_link(learner_id(x_learner_id), b.url.strip())}


@app.get("/library/docs")
def library_docs(x_learner_id: str | None = Header(None)):
    return library.list_docs(learner_id(x_learner_id))


@app.delete("/library/docs/{doc_id}")
def library_delete(doc_id: str, x_learner_id: str | None = Header(None)):
    if not library.delete_doc(learner_id(x_learner_id), doc_id):
        raise HTTPException(404, "Not found")
    return {"ok": True}


@app.post("/cards/{card_id}/review")
def review(card_id: int, b: Review, x_learner_id: str | None = Header(None)):
    r = flashcards.review(learner_id(x_learner_id), card_id, max(0, min(5, b.quality)))
    if not r:
        raise HTTPException(404, "Card not found")
    return r


class MockStart(BaseModel):
    preset: str = "quick"


class MockAnswer(BaseModel):
    question_id: str
    choice: int | None = None


@app.post("/mock/start")
def mock_start(b: MockStart, x_learner_id: str | None = Header(None)):
    if b.preset not in mock.PRESETS:
        raise HTTPException(400, f"preset must be one of {list(mock.PRESETS)}")
    m = mock.start(learner_id(x_learner_id), b.preset)
    if not m:
        raise HTTPException(404, "No questions available yet")
    return m


@app.get("/mock/history")
def mock_history(x_learner_id: str | None = Header(None)):
    return mock.history(learner_id(x_learner_id))


@app.get("/mock/{mock_id}")
def mock_get(mock_id: str, x_learner_id: str | None = Header(None)):
    m = mock.view(learner_id(x_learner_id), mock_id)
    if not m:
        raise HTTPException(404, "Mock not found")
    return m


@app.put("/mock/{mock_id}/answer")
def mock_answer(mock_id: str, b: MockAnswer, x_learner_id: str | None = Header(None)):
    r = mock.answer(learner_id(x_learner_id), mock_id, b.question_id, b.choice)
    if r == "missing":
        raise HTTPException(404, "Mock not found")
    if r == "closed":
        raise HTTPException(409, "Time is up or the exam was submitted")
    return {"ok": True}


@app.post("/mock/{mock_id}/submit")
def mock_submit(mock_id: str, x_learner_id: str | None = Header(None)):
    r = mock.submit(learner_id(x_learner_id), mock_id)
    if not r:
        raise HTTPException(404, "Mock not found")
    return r


@app.get("/mock/{mock_id}/result")
def mock_result(mock_id: str, x_learner_id: str | None = Header(None)):
    r = mock.result(learner_id(x_learner_id), mock_id)
    if not r:
        raise HTTPException(404, "Mock not found")
    return r
