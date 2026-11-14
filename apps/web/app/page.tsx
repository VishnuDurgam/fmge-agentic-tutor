import Link from "next/link";

const items = [
  ["/library", "My material", "Upload PDFs, photos of notes or a link. Scanned pages are read automatically, then the tutor and question maker use them."],
  ["/chat", "AI Tutor", "Ask any FMGE topic and get an exam-focused answer grounded in your notes."],
  ["/practice", "Adaptive Q-bank", "Practice MCQs. The next question targets your weak topics."],
  ["/mock", "Timed Mock Exams", "FMGE-style timed tests with a question palette; explanations and subject-wise score after you submit."],
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
