"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Q = { id: string; subject: string; topic: string; stem: string; options: string[]; reviewed: boolean };
type R = { correct: boolean; answer: number; explanation: string; ai_feedback: string; reviewed: boolean; source?: string };

export default function Practice() {
  const [subjects, setSubjects] = useState<string[]>([]);
  const [subject, setSubject] = useState("");
  const [q, setQ] = useState<Q | null>(null);
  const [picked, setPicked] = useState<number | null>(null);
  const [res, setRes] = useState<R | null>(null);
  const [err, setErr] = useState("");
  const [topic, setTopic] = useState("");
  const [gen, setGen] = useState("");
  const [sources, setSources] = useState<{ name: string; mine: boolean }[]>([]);
  const [source, setSource] = useState("");

  async function load(s = subject) {
    setPicked(null); setRes(null); setErr("");
    try { setQ(await api<Q>("/quiz/next" + (s ? `?subject=${encodeURIComponent(s)}` : ""))); }
    catch { setQ(null); setErr("No questions for this subject yet."); }
  }
  useEffect(() => { api<string[]>("/subjects").then(setSubjects).catch(() => {}); api<{ sources: { name: string; mine: boolean }[] }>("/library/stats").then((l) => setSources(l.sources)).catch(() => {}); load(""); }, []);

  async function pick(i: number) {
    if (!q || res) return;
    setPicked(i);
    setRes(await api<R>("/quiz/submit", { method: "POST", body: JSON.stringify({ question_id: q.id, choice: i }) }));
  }

  async function generate() {
    setGen("Reading the books and writing questions...");
    try {
      const r = await api<{ made: unknown[]; x?: never }>("/quiz/generate", { method: "POST", body: JSON.stringify({ topic, source, n: 5 }) });
      setGen(r.made.length ? `Added ${r.made.length} new draft questions` : "No questions made. Try a different topic or material.");
      load();
    } catch (e) { setGen(String(e)); }
  }

  return (
    <>
      <h2>Practice</h2>
      <select value={subject} onChange={(e) => { setSubject(e.target.value); load(e.target.value); }}>
        <option value="">All subjects (adaptive)</option>
        {subjects.map((s) => <option key={s}>{s}</option>)}
      </select>
      <div className="card">
        <strong>Make new questions from your study material</strong>
        <div className="row"><select value={source} onChange={(e) => setSource(e.target.value)}><option value="">All material</option>{sources.map((x) => <option key={x.name} value={x.name}>{x.name}{x.mine ? " (mine)" : ""}</option>)}</select></div>
        <div className="row" style={{ marginTop: 8 }}><input style={{ flex: 1 }} value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic, e.g. cardiac output (blank = random)" /><button onClick={generate}>Generate 5</button></div>
        {gen && <p className="muted">{gen}</p>}
      </div>
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
              {res.source && <p className="muted">Source: {res.source}</p>}
              <p><button onClick={() => load()}>Next question</button></p>
            </>
          )}
        </div>
      )}
    </>
  );
}
