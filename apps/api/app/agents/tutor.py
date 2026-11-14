"""LangGraph tutor, library first: retrieve from the ingested books/notes, then answer from them.

If nothing relevant is found, the answer is clearly flagged as general knowledge (not from the library).
"""
from typing import TypedDict

from langgraph.graph import END, StateGraph

from .. import llm, retrieval

SYSTEM = (
    "You are an FMGE (India) exam tutor for MBBS graduates. Answer ONLY from the numbered library "
    "excerpts when they are relevant, and cite them like [1], [2]. Be exam-focused: the high-yield "
    "point first, then a short explanation and a memory hook. If the excerpts do not cover the "
    "question, begin with 'Not found in the library:' and give a brief general answer, flagging "
    "uncertainty. This is study support, not clinical advice."
)


class State(TypedDict, total=False):
    question: str
    subject: str
    learner: str
    source: str
    context: list
    answer: str


def retrieve(s: State) -> State:
    return {"context": retrieval.search_all((s.get("subject", "") + " " + s["question"]).strip(), 5, s.get("learner"), s.get("source") or None)}


def answer(s: State) -> State:
    ctx = "\n\n".join(f"[{i+1}] {c['source']} / {c.get('title','')}: {c['text']}" for i, c in enumerate(s.get("context", [])))
    prompt = f"Library excerpts:\n{ctx or '(none found)'}\n\nQuestion: {s['question']}"
    return {"answer": llm.complete(SYSTEM, prompt, 1000)}


def _build():
    g = StateGraph(State)
    g.add_node("retrieve", retrieve)
    g.add_node("answer", answer)
    g.set_entry_point("retrieve")
    g.add_edge("retrieve", "answer")
    g.add_edge("answer", END)
    return g.compile()


_graph = _build()


def ask(question: str, subject: str = "", learner: str = "", source: str = "") -> dict:
    out = _graph.invoke({"question": question, "subject": subject, "learner": learner, "source": source})
    return {
        "answer": out["answer"],
        "from_library": bool(out.get("context")),
        "sources": [{"source": c["source"], "title": c.get("title", ""), "snippet": c["text"][:200]}
                    for c in out.get("context", [])],
    }
