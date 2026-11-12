import "./globals.css";
import Link from "next/link";
import type { Metadata, Viewport } from "next";

export const metadata: Metadata = {
  title: "FMGE Agentic Tutor",
  description: "AI tutor, adaptive Q-bank, study planner and flashcards for FMGE preparation",
  manifest: "/manifest.webmanifest",
};
export const viewport: Viewport = { themeColor: "#0f766e", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav>
          <Link href="/">Home</Link>
          <Link href="/chat">Tutor</Link>
          <Link href="/practice">Practice</Link>
          <Link href="/planner">Planner</Link>
          <Link href="/cards">Flashcards</Link>
        </nav>
        <main>{children}</main>
        <script dangerouslySetInnerHTML={{ __html: "if('serviceWorker' in navigator){navigator.serviceWorker.register('/sw.js')}" }} />
      </body>
    </html>
  );
}
