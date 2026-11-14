# FMGE Agentic Tutor

AI study companion for FMGE aspirants: library-grounded tutor, adaptive question bank, timed FMGE-format mock exams, study planner and spaced-repetition flashcards. FastAPI + LangGraph backend, Next.js website, Expo mobile app.

Built as a personal project to help my brother and others preparing for the exam.

## Features
- **Library first**: downloads open-licence textbooks (OpenStax) plus your own notes, indexes them, and everything below works from that library with source citations.
- **AI tutor**: LangGraph agent (retrieve then answer); says 'Not found in the library' when it has to fall back to general knowledge.
- **My material**: upload PDFs, photos of notes or a link from the phone or website; scanned pages are OCR'd, then the tutor, question generator and a "My material" mock use them (see STUDY_MATERIAL.md).
- **Question generator**: reads passages from any loaded material (pick a book or workbook) and writes exam-style MCQs and flashcards with explanations, saved as drafts for review.
- **Timed mock exams**: FMGE format (4-option MCQs, +1, no negative marking, pass at 50%), question palette, mark for review, auto-submit when time ends, explanations and subject-wise score after submitting. Presets: quick (20 Q), section (50 Q), Part A and Part B (150 Q, 150 min).
- **Adaptive Q-bank**: next question is weighted toward your weak topics; wrong answers get AI feedback.
- **Study planner**: splits days across the 19 FMGE subjects by weightage and your accuracy, with a revision block.
- **Flashcards**: SM-2 spaced repetition, plus AI card generation.
- One FastAPI backend, served to a **Next.js website (installable PWA)** and an **Expo (React Native) mobile app**.

## Layout
```
apps/api      FastAPI + LangGraph backend (SQLite)
apps/web      Next.js website / PWA
apps/mobile   Expo app for Android and iOS
content/      seed questions, raw notes to ingest, SOURCES.md
```

## Run locally
```bash
# API
cd apps/api && python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
export GEMINI_API_KEY=...         # free key from aistudio.google.com (or GROQ_API_KEY / OPENROUTER_API_KEY), no card needed
python ../../content/tools/fetch_open_books.py   # download open textbooks into content/raw
python -m app.ingest              # index them (and any notes you add) for retrieval
python -m app.gen_cli 10          # optional: pre-generate 10 draft questions from the books
uvicorn app.main:app --reload     # http://localhost:8000/docs

# Web
cd apps/web && cp .env.example .env.local && npm install && npm run dev

# Mobile
cd apps/mobile && npm install && npx expo start
```
Tests: `cd apps/api && python -m pytest`.

## Deploy
1. **API on Render**: New Blueprint from this repo (uses `render.yaml`). Set `GEMINI_API_KEY` (and optionally `GROQ_API_KEY` as backup) and set `CORS_ORIGINS` to your web URL. The 1 GB disk keeps the SQLite database.
2. **Website on Vercel**: import the repo, set root directory `apps/web`, add `NEXT_PUBLIC_API_URL=https://<your-api>.onrender.com`.
3. **Mobile**: set `extra.apiUrl` in `apps/mobile/app.json`, then `npx eas build -p android --profile preview` for an APK, and `eas submit` for Play Store / App Store.

## Zero cost
Runs on free tiers only: Gemini / Groq / OpenRouter free API keys (the app falls through to the next provider when one is rate limited), Vercel hobby for the website, and Expo / EAS free plan for builds. Free plans on hosts like Render sleep when idle and have no persistent disk, so progress data can reset; move to a free Postgres (Neon or Supabase) when you add login. Free API tiers may use your prompts to improve their products, so never send student personal data.

## Content and licensing
See `content/SOURCES.md`. Sample questions in `content/seed/` are original drafts marked `reviewed: 0`; have a doctor review them before real use. Do not commit copyrighted books or paid course material.

## Roadmap
Real accounts (login) and cloud database, doctor review workflow for questions, image-based questions, PYQ topic weightage from real data, push reminders for due cards, mock tests with timers.

Study support only, not medical advice.
