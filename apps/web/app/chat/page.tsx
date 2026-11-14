"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Turn = { q: string; a: string; lib: boolean; sources: { source: string; title: string; snippet: string }[] };

export default function Chat() {
  const [q, setQ] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [source, setSource] = useState("");
  useEffect(() => { setSource(new URLSearchParams(window.location.search).get("source") || ""); }, []);

  async function send() {
    if (!q.trim()) return;
    setBusy(true); setErr("");
    try {
      const r = await api<{ answer: string; from_library: boolean; sources: Turn["sources"] }>("/tutor/ask", { method: "POST", body: JSON.stringify({ question: q, source }) });
      setTurns([{ q, a: r.answer, lib: r.from_library, sources: r.sources }, ...turns]);
      setQ("");
    } catch (e) { setErr(String(e)); }
    setBusy(false);
  }

  return (
    <>
      <h2>AI Tutor</h2>
      {source && <div className="notice">Answering from: {source} <button onClick={() => setSource("")}>Use everything</button></div>}
      <div className="row">
        <input style={{ flex: 1, minWidth: 200 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Antidote for magnesium toxicity?" onKeyDown={(e) => e.key === "Enter" && send()} />
        <button onClick={send} disabled={busy}>{busy ? "Thinking..." : "Ask"}</button>
      </div>
      {err && <p style={{ color: "var(--bad)" }}>{err}</p>}
      {turns.map((t, i) => (
        <div className="card" key={i}>
          <div className="me">{t.q}</div>
          <div className="msg">{t.a}</div>
          {t.lib ? <div className="muted">From library: {t.sources.map((s) => `${s.title} (${s.source})`).join("; ")}</div> : <div className="notice">Not found in the library. This is a general answer, verify it.</div>}
        </div>
      ))}
    </>
  );
}
