"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Q = { id: string; subject: string; topic: string; stem: string; options: string[]; reviewed: boolean };
type R = { correct: boolean; answer: number; explanation: string; ai_feedback: string };

export default function Practice() {
  const [subjects, setSubjects] = useState<string[]>([]);
  const [subject, setSubject] = useState("");
  const [q, setQ] = useState<Q | null>(null);
  const [picked, setPicked] = useState<number | null>(null);
  const [res, setRes] = useState<R | null>(null);
  const [err, setErr] = useState("");

  async function load(s = subject) {
    setPicked(null); setRes(null); setErr("");
    try { setQ(await api<Q>("/quiz/next" + (s ? `?subject=${encodeURIComponent(s)}` : ""))); }
    catch { setQ(null); setErr("No questions for this subject yet."); }
  }
  useEffect(() => { api<string[]>("/subjects").then(setSubjects).catch(() => {}); load(""); }, []);

  async function pick(i: number) {
    if (!q || res) return;
    setPicked(i);
    setRes(await api<R>("/quiz/submit", { method: "POST", body: JSON.stringify({ question_id: q.id, choice: i }) }));
  }

  return (
    <>
      <h2>Practice</h2>
      <select value={subject} onChange={(e) => { setSubject(e.target.value); load(e.target.value); }}>
        <option value="">All subjects (adaptive)</option>
        {subjects.map((s) => <option key={s}>{s}</option>)}
      </select>
      {err && <p className="muted">{err}</p>}
      {q && (
        <div className="card">
          <div className="muted">{q.subject} / {q.topic}</div>
          <p><strong>{q.stem}</strong></p>
          {q.options.map((o, i) => (
            <button key={i} className={"opt" + (res ? (i === res.answer ? " good" : i === picked ? " bad" : "") : "")} onClick={() => pick(i)}>
              {String.fromCharCode(65 + i)}. {o}
            </button>
          ))}
          {res && (
            <>
              <p><strong>{res.correct ? "Correct" : "Incorrect"}</strong>. {res.explanation}</p>
              {res.ai_feedback && <p className="msg">{res.ai_feedback}</p>}
              {!q.reviewed && <div className="notice">Draft question, not yet reviewed by a doctor. Verify before relying on it.</div>}
              <p><button onClick={() => load()}>Next question</button></p>
            </>
          )}
        </div>
      )}
    </>
  );
}
