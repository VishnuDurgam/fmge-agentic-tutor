"""LangGraph tutor: retrieve -> answer (grounded) -> optional flashcard suggestions."""
from typing import TypedDict

from langgraph.graph import END, StateGraph

from .. import llm, retrieval

SYSTEM = (
    "You are an FMGE (India) exam tutor for MBBS graduates. Be accurate, concise and "
    "exam-focused: lead with the high-yield point, then a short explanation and a memory hook. "
    "Use the provided context when relevant and cite it as [1], [2]. If the context does not "
    "cover the question, say so and answer from standard medical knowledge, flagging uncertainty. "
    "This is study support, not clinical advice."
)


class State(TypedDict, total=False):
    question: str
    subject: str
    context: list
    answer: str


def retrieve(s: State) -> State:
    q = (s.get("subject", "") + " " + s["question"]).strip()
    return {"context": retrieval.search(q, k=4)}


def answer(s: State) -> State:
    ctx = "\n\n".join(f"[{i+1}] ({c['source']}) {c['text']}" for i, c in enumerate(s.get("context", [])))
    prompt = f"Context:\n{ctx or '(none)'}\n\nQuestion: {s['question']}"
    return {"answer": llm.complete(SYSTEM, prompt)}


def _build():
    g = StateGraph(State)
    g.add_node("retrieve", retrieve)
    g.add_node("answer", answer)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", END)
    return g.compile()


_graph = _build()


def ask(question: str, subject: str = "") -> dict:
    out = _graph.invoke({"question": question, "subject": subject})
    return {
        "answer": out["answer"],
        "sources": [{"source": c["source"], "snippet": c["text"][:200]} for c in out.get("context", [])],
    }
