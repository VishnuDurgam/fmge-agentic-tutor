from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import llm
from .agents import flashcards, planner, quiz, tutor
from .config import CORS_ORIGINS, SUBJECTS
from .db import init_db

app = FastAPI(title="FMGE Agentic Tutor API")
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_methods=["*"], allow_headers=["*"])


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
    return {"ok": True, "ai": llm.available()}


@app.get("/subjects")
def subjects():
    return SUBJECTS


@app.post("/tutor/ask")
def ask(b: Ask, x_learner_id: str | None = Header(None)):
    learner_id(x_learner_id)
    return tutor.ask(b.question, b.subject)


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
    return flashcards.generate(learner_id(x_learner_id), b.topic, b.subject, min(b.n, 10))


@app.post("/cards/{card_id}/review")
def review(card_id: int, b: Review, x_learner_id: str | None = Header(None)):
    r = flashcards.review(learner_id(x_learner_id), card_id, max(0, min(5, b.quality)))
    if not r:
        raise HTTPException(404, "Card not found")
    return r
