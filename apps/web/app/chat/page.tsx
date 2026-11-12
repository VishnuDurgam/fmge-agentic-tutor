"use client";
import { useState } from "react";
import { api } from "@/lib/api";

type Turn = { q: string; a: string; sources: { source: string; snippet: string }[] };

export default function Chat() {
  const [q, setQ] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function send() {
    if (!q.trim()) return;
    setBusy(true); setErr("");
    try {
      const r = await api<{ answer: string; sources: Turn["sources"] }>("/tutor/ask", { method: "POST", body: JSON.stringify({ question: q }) });
      setTurns([{ q, a: r.answer, sources: r.sources }, ...turns]);
      setQ("");
    } catch (e) { setErr(String(e)); }
    setBusy(false);
  }

  return (
    <>
      <h2>AI Tutor</h2>
      <div className="row">
        <input style={{ flex: 1, minWidth: 200 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Antidote for magnesium toxicity?" onKeyDown={(e) => e.key === "Enter" && send()} />
        <button onClick={send} disabled={busy}>{busy ? "Thinking..." : "Ask"}</button>
      </div>
      {err && <p style={{ color: "var(--bad)" }}>{err}</p>}
      {turns.map((t, i) => (
        <div className="card" key={i}>
          <div className="me">{t.q}</div>
          <div className="msg">{t.a}</div>
          {t.sources.length > 0 && <div className="muted">Sources: {t.sources.map((s) => s.source).join(", ")}</div>}
        </div>
      ))}
    </>
  );
}
