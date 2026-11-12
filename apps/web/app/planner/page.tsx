"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Plan = { days_left: number; study_days: number; revision_days: number; plan: { subject: string; days: number; hours: number }[]; daily_routine: string[]; note?: string };

export default function Planner() {
  const [date, setDate] = useState("");
  const [hours, setHours] = useState(4);
  const [plan, setPlan] = useState<Plan | null>(null);

  const load = () => api<Plan>("/planner/plan").then(setPlan).catch(() => setPlan(null));
  useEffect(() => { load(); }, []);

  async function save() {
    await api("/planner/profile", { method: "PUT", body: JSON.stringify({ exam_date: date, hours_per_day: hours }) });
    load();
  }

  return (
    <>
      <h2>Study Planner</h2>
      <div className="row">
        <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <input type="number" min={1} max={16} step={0.5} value={hours} onChange={(e) => setHours(+e.target.value)} style={{ width: 90 }} />
        <span className="muted" style={{ alignSelf: "center" }}>hours/day</span>
        <button onClick={save} disabled={!date}>Build plan</button>
      </div>
      {plan && (
        <div className="card">
          <p><strong>{plan.days_left} days left</strong> ({plan.study_days} study, {plan.revision_days} revision)</p>
          {plan.note && <p>{plan.note}</p>}
          {plan.plan.map((p) => <div key={p.subject} className="row" style={{ justifyContent: "space-between" }}><span>{p.subject}</span><span className="muted">{p.days} days, {p.hours} h</span></div>)}
          <p className="muted">Daily: {plan.daily_routine?.join(" | ")}</p>
        </div>
      )}
    </>
  );
}
