import Link from "next/link";

const items = [
  ["/chat", "AI Tutor", "Ask any FMGE topic and get an exam-focused answer grounded in your notes."],
  ["/practice", "Adaptive Q-bank", "Practice MCQs. The next question targets your weak topics."],
  ["/planner", "Study Planner", "Enter your exam date and get a subject-wise plan that adapts to your scores."],
  ["/cards", "Flashcards", "Spaced repetition cards, with AI generation for any topic."],
];

export default function Home() {
  return (
    <>
      <h1>FMGE Agentic Tutor</h1>
      <p className="muted">Free study companion for FMGE aspirants. Study support only, not clinical advice.</p>
      {items.map(([href, t, d]) => (
        <Link key={href} href={href} style={{ textDecoration: "none", color: "inherit" }}>
          <div className="card"><strong>{t}</strong><div className="muted">{d}</div></div>
        </Link>
      ))}
    </>
  );
}
