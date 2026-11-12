"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Card = { id: number; front: string; back: string };

export default function Cards() {
  const [due, setDue] = useState<Card[]>([]);
  const [flip, setFlip] = useState(false);
  const [topic, setTopic] = useState("");
  const [front, setFront] = useState("");
  const [back, setBack] = useState("");
  const [msg, setMsg] = useState("");

  const load = () => api<Card[]>("/cards/due").then((d) => { setDue(d); setFlip(false); });
  useEffect(() => { load(); }, []);

  async function rate(quality: number) {
    await api(`/cards/${due[0].id}/review`, { method: "POST", body: JSON.stringify({ quality }) });
    load();
  }
  async function gen() {
    const r = await api<Card[]>("/cards/generate", { method: "POST", body: JSON.stringify({ topic }) });
    setMsg(r.length ? `Added ${r.length} cards` : "AI generation needs ANTHROPIC_API_KEY on the server");
    load();
  }
  async function add() {
    await api("/cards", { method: "POST", body: JSON.stringify({ front, back }) });
    setFront(""); setBack(""); load();
  }

  return (
    <>
      <h2>Flashcards</h2>
      {due[0] ? (
        <div className="card">
          <div className="muted">{due.length} due</div>
          <p><strong>{due[0].front}</strong></p>
          {flip ? (
            <>
              <p>{due[0].back}</p>
              <div className="row">
                <button className="alt" onClick={() => rate(1)}>Again</button>
                <button className="alt" onClick={() => rate(3)}>Hard</button>
                <button onClick={() => rate(4)}>Good</button>
                <button onClick={() => rate(5)}>Easy</button>
              </div>
            </>
          ) : <button onClick={() => setFlip(true)}>Show answer</button>}
        </div>
      ) : <p className="muted">No cards due. Add some below.</p>}
      <div className="card">
        <strong>Generate with AI</strong>
        <div className="row"><input value={topic} onChange={(e) => setTopic(e.target.value)} placeholder="Topic, e.g. Nerve injuries of upper limb" style={{ flex: 1 }} /><button onClick={gen} disabled={!topic}>Generate</button></div>
        {msg && <p className="muted">{msg}</p>}
      </div>
      <div className="card">
        <strong>Add manually</strong>
        <div className="row"><input value={front} onChange={(e) => setFront(e.target.value)} placeholder="Front" style={{ flex: 1 }} /><input value={back} onChange={(e) => setBack(e.target.value)} placeholder="Back" style={{ flex: 1 }} /><button onClick={add} disabled={!front || !back}>Add</button></div>
      </div>
    </>
  );
}
