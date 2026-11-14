"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type Q = { pos: number; id: string; subject: string; stem: string; options: string[]; choice: number | null };
type Exam = { id: string; preset: string; status: string; seconds_left: number; total: number; requested?: number; questions: Q[] };
type Result = {
  status: string; score: number; total: number; answered: number; percent: number; pass_mark: number; passed: boolean;
  by_subject: { subject: string; correct: number; total: number }[];
  review: { pos: number; stem: string; options: string[]; chosen: number | null; answer: number; explanation: string; source: string; reviewed: boolean }[];
};

const PRESETS: [string, string, string][] = [
  ["quick", "Quick test", "20 questions, 20 minutes"],
  ["my_material", "My material", "20 questions made from what you uploaded"],
  ["section", "Section", "50 questions, 50 minutes"],
  ["part_a", "Part A (pre and para-clinical)", "150 questions, 150 minutes"],
  ["part_b", "Part B (clinical)", "150 questions, 150 minutes"],
];
const fmt = (s: number) => `${Math.floor(s / 3600) ? Math.floor(s / 3600) + ":" : ""}${String(Math.floor((s % 3600) / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

export default function Mock() {
  const [exam, setExam] = useState<Exam | null>(null);
  const [res, setRes] = useState<Result | null>(null);
  const [i, setI] = useState(0);
  const [left, setLeft] = useState(0);
  const [flags, setFlags] = useState<Set<string>>(new Set());
  const [err, setErr] = useState("");
  const submitting = useRef(false);

  const finish = useCallback(async (id: string) => {
    if (submitting.current) return;
    submitting.current = true;
    try { setRes(await api<Result>(`/mock/${id}/submit`, { method: "POST" })); localStorage.removeItem("fmge_mock"); }
    catch (e) { setErr(String(e)); }
    submitting.current = false;
  }, []);

  const load = useCallback(async (id: string) => {
    const e = await api<Exam>(`/mock/${id}`);
    if (e.status === "submitted") { setRes(await api<Result>(`/mock/${id}/result`)); localStorage.removeItem("fmge_mock"); return; }
    setExam(e); setLeft(e.seconds_left);
  }, []);

  useEffect(() => { const id = localStorage.getItem("fmge_mock"); if (id) load(id).catch(() => localStorage.removeItem("fmge_mock")); }, [load]);

  useEffect(() => {
    if (!exam || res) return;
    const t = setInterval(() => setLeft((l) => Math.max(0, l - 1)), 1000);
    return () => clearInterval(t);
  }, [exam, res]);
  useEffect(() => { if (exam && !res && left === 0) finish(exam.id); }, [left, exam, res, finish]);

  async function start(preset: string) {
    setErr(""); setRes(null); setI(0); setFlags(new Set());
    try {
      const e = await api<Exam>("/mock/start", { method: "POST", body: JSON.stringify({ preset }) });
      localStorage.setItem("fmge_mock", e.id); setExam(e); setLeft(e.seconds_left);
    } catch (x) { setErr(String(x)); }
  }

  async function pick(q: Q, choice: number) {
    if (!exam) return;
    const next = q.choice === choice ? null : choice; // tap again to clear
    setExam({ ...exam, questions: exam.questions.map((x) => (x.id === q.id ? { ...x, choice: next } : x)) });
    api(`/mock/${exam.id}/answer`, { method: "PUT", body: JSON.stringify({ question_id: q.id, choice: next }) }).catch((e) => setErr(String(e)));
  }

  if (res) {
    return (
      <>
        <h2>Result</h2>
        <div className="card">
          <p style={{ fontSize: "1.6rem", margin: 0 }}><strong>{res.score} / {res.total}</strong> ({res.percent}%)</p>
          <p style={{ color: res.passed ? "var(--good)" : "var(--bad)" }}><strong>{res.passed ? "Pass" : "Below pass mark"}</strong> <span className="muted">(pass mark {res.pass_mark}, no negative marking, {res.answered} answered)</span></p>
          {res.by_subject.map((s) => <div key={s.subject} className="row" style={{ justifyContent: "space-between" }}><span>{s.subject}</span><span className="muted">{s.correct}/{s.total}</span></div>)}
          <p><button onClick={() => { setRes(null); setExam(null); }}>New mock</button></p>
        </div>
        <h3>Review with explanations</h3>
        {res.review.map((r) => (
          <div className="card" key={r.pos}>
            <p><strong>{r.pos}. {r.stem}</strong></p>
            {r.options.map((o, k) => <div key={k} className={"opt" + (k === r.answer ? " good" : k === r.chosen ? " bad" : "")} style={{ padding: 8, borderRadius: 8, border: "1px solid var(--line)", margin: "4px 0" }}>{String.fromCharCode(65 + k)}. {o}{k === r.chosen ? " (your answer)" : ""}</div>)}
            {r.chosen === null && <p className="muted">Not answered</p>}
            <p>{r.explanation}</p>
            <p className="muted">Source: {r.source}</p>
            {!r.reviewed && <div className="notice">Draft question, not yet reviewed by a doctor.</div>}
          </div>
        ))}
      </>
    );
  }

  if (!exam) {
    return (
      <>
        <h2>Mock exam</h2>
        <p className="muted">FMGE format: 4-option MCQs, 1 mark each, no negative marking, pass at 50%. Explanations appear after you submit. The real exam has 300 questions in two parts of 150 questions and 150 minutes each.</p>
        {err && <p style={{ color: "var(--bad)" }}>{err}</p>}
        {PRESETS.map(([k, t, d]) => (
          <div className="card" key={k}><strong>{t}</strong><div className="muted">{d}</div><p><button onClick={() => start(k)}>Start</button></p></div>
        ))}
        <p className="muted">If the question bank has fewer questions than a preset needs, the test uses what is available. Load more with MedMCQA or the question generator.</p>
      </>
    );
  }

  const q = exam.questions[i];
  const answered = exam.questions.filter((x) => x.choice !== null).length;
  return (
    <>
      <div className="row" style={{ justifyContent: "space-between", position: "sticky", top: 52, background: "var(--bg)", padding: "8px 0", zIndex: 1 }}>
        <strong>Question {i + 1} of {exam.total}</strong>
        <strong style={{ color: left < 300 ? "var(--bad)" : "inherit" }}>{fmt(left)}</strong>
      </div>
      {err && <p style={{ color: "var(--bad)" }}>{err}</p>}
      <div className="card">
        <div className="muted">{q.subject}</div>
        <p><strong>{q.stem}</strong></p>
        {q.options.map((o, k) => (
          <button key={k} className={"opt" + (q.choice === k ? " good" : "")} onClick={() => pick(q, k)}>{String.fromCharCode(65 + k)}. {o}</button>
        ))}
        <div className="row" style={{ marginTop: 8 }}>
          <button className="alt" disabled={i === 0} onClick={() => setI(i - 1)}>Previous</button>
          <button className="alt" onClick={() => setFlags((f) => { const n = new Set(f); n.has(q.id) ? n.delete(q.id) : n.add(q.id); return n; })}>{flags.has(q.id) ? "Unmark review" : "Mark for review"}</button>
          <button disabled={i === exam.total - 1} onClick={() => setI(i + 1)}>Next</button>
        </div>
      </div>
      <div className="card">
        <div className="muted">{answered} answered, {flags.size} marked. Green = answered, orange = marked for review.</div>
        <div className="row" style={{ marginTop: 8 }}>
          {exam.questions.map((x, k) => (
            <button key={x.id} onClick={() => setI(k)} style={{ width: 38, padding: 6, background: flags.has(x.id) ? "#f59e0b" : x.choice !== null ? "var(--good)" : "#fff", color: x.choice !== null || flags.has(x.id) ? "#fff" : "var(--ink)", border: k === i ? "2px solid var(--ink)" : "1px solid var(--line)" }}>{k + 1}</button>
          ))}
        </div>
        <p><button onClick={() => confirm(`Submit now? ${exam.total - answered} unanswered.`) && finish(exam.id)} style={{ background: "var(--bad)" }}>Submit exam</button></p>
      </div>
    </>
  );
}
