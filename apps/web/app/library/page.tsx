"use client";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

type Doc = { id: string; name: string; kind: string; status: string; pages_done: number; pages_total: number; error: string | null };

export default function Library() {
  const [docs, setDocs] = useState<Doc[]>([]);
  const [url, setUrl] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [gen, setGen] = useState("");
  const [code, setCode] = useState("");
  useEffect(() => { setCode(localStorage.getItem("fmge_private") || ""); }, []);

  const refresh = useCallback(() => api<Doc[]>("/library/docs").then(setDocs).catch(() => {}), []);
  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => {
    if (!docs.some((d) => d.status === "processing")) return;
    const t = setInterval(refresh, 2500);
    return () => clearInterval(t);
  }, [docs, refresh]);

  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true); setMsg("");
    for (const f of Array.from(files)) {
      const fd = new FormData();
      fd.append("file", f);
      try { await api("/library/upload", { method: "POST", body: fd }); } catch (e) { setMsg(`${f.name}: ${e}`); }
    }
    setBusy(false); refresh();
  }

  async function addLink() {
    if (!url.trim()) return;
    try { await api("/library/link", { method: "POST", body: JSON.stringify({ url }) }); setUrl(""); refresh(); } catch (e) { setMsg(String(e)); }
  }

  async function makeQuestions(d: Doc) {
    setGen(`Writing questions from ${d.name}...`);
    try {
      const r = await api<{ made: unknown[] }>("/quiz/generate", { method: "POST", body: JSON.stringify({ source: d.name, n: 5 }) });
      setGen(r.made.length ? `Added ${r.made.length} questions from ${d.name}. Find them in Practice, or take a "My material" mock exam.` : "No questions made. Try again or pick another file.");
    } catch (e) { setGen(String(e)); }
  }

  async function remove(d: Doc) { await api(`/library/docs/${d.id}`, { method: "DELETE" }); refresh(); }

  return (
    <>
      <h2>My material</h2>
      <p className="muted">Add PDFs, photos of notes, text files or a web link. Scanned pages are read automatically. This stays with your device ID, and other people cannot see it.</p>
      <div className="card">
        <b>Private notes</b>
        <p className="muted" style={{ margin: "4px 0" }}>If you were given a private code, enter it to use the private notes in the tutor, practice and mock exams.</p>
        <div className="row">
          <input type="password" placeholder="Private code" value={code} onChange={(e) => setCode(e.target.value)} style={{ flex: 1 }} />
          <button onClick={() => { localStorage.setItem("fmge_private", code.trim()); setMsg(code.trim() ? "Private notes unlocked on this device." : "Private notes locked."); }}>Save</button>
        </div>
      </div>
      <div className="card">
        <label className="row" style={{ cursor: "pointer" }}>
          <input type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.md,application/pdf,image/*" onChange={(e) => { upload(e.target.files); e.target.value = ""; }} disabled={busy} style={{ flex: 1 }} />
        </label>
        <div className="row" style={{ marginTop: 8 }}>
          <input style={{ flex: 1 }} value={url} onChange={(e) => setUrl(e.target.value)} placeholder="Paste a link (web page, PDF, or Google Drive share link)" />
          <button onClick={addLink}>Add</button>
        </div>
        {msg && <p className="muted">{msg}</p>}
      </div>
      {gen && <div className="notice">{gen}</div>}
      {docs.map((d) => (
        <div className="card" key={d.id}>
          <strong>{d.name}</strong>
          <div className="muted">
            {d.status === "processing" && `Reading... ${d.pages_done}/${d.pages_total || "?"} pages`}
            {d.status === "ready" && `Ready (${d.pages_total} page${d.pages_total === 1 ? "" : "s"})`}
            {d.status === "error" && `Problem: ${d.error}`}
          </div>
          <div className="row" style={{ marginTop: 8 }}>
            {d.status === "ready" && <button onClick={() => makeQuestions(d)}>Make 5 questions</button>}
            {d.status === "ready" && <Link href={`/chat?source=${encodeURIComponent(d.name)}`}><button>Ask the tutor</button></Link>}
            <button onClick={() => remove(d)}>Delete</button>
          </div>
        </div>
      ))}
      {!docs.length && <p className="muted">Nothing added yet.</p>}
    </>
  );
}
