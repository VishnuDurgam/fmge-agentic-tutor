"use client";
import { useEffect, useState } from "react";
import { BASE, api } from "@/lib/api";

// If the server has APP_PASSCODE set, ask for the access code once and remember it on this device.
export default function Gate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<"checking" | "locked" | "open">("checking");
  const [code, setCode] = useState("");
  const [err, setErr] = useState("");

  async function verify() {
    try { await api("/auth/check"); setState("open"); setErr(""); }
    catch { setState("locked"); }
  }

  useEffect(() => {
    fetch(BASE + "/health").then((r) => r.json())
      .then((h) => (h.locked ? verify() : setState("open")))
      .catch(() => setState("open"));
  }, []);

  if (state === "open") return <>{children}</>;
  if (state === "checking") return <p className="muted">Loading...</p>;
  return (
    <div className="card">
      <h2>Private study app</h2>
      <p className="muted">Enter your access code.</p>
      <div className="row">
        <input type="password" value={code} onChange={(e) => setCode(e.target.value)} onKeyDown={(e) => e.key === "Enter" && go()} />
        <button onClick={go}>Enter</button>
      </div>
      {err && <p style={{ color: "var(--bad)" }}>{err}</p>}
    </div>
  );

  async function go() {
    localStorage.setItem("fmge_code", code);
    try { await api("/auth/check"); setState("open"); } catch { localStorage.removeItem("fmge_code"); setErr("Wrong code"); }
  }
}
