# FMGE Agentic Tutor

A free, open study companion for FMGE aspirants, built as a personal project to help my brother and others preparing for the exam.

## Features
- **AI tutor**: LangGraph agent (retrieve then answer) grounded in your own notes via BM25 search, with source citations.
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
export ANTHROPIC_API_KEY=sk-...   # optional; without it the app runs in offline mode
python -m app.ingest              # build the retrieval index from content/raw
uvicorn app.main:app --reload     # http://localhost:8000/docs

# Web
cd apps/web && cp .env.example .env.local && npm install && npm run dev

# Mobile
cd apps/mobile && npm install && npx expo start
```
Tests: `cd apps/api && python -m pytest`.

## Deploy
1. **API on Render**: New Blueprint from this repo (uses `render.yaml`). Set `ANTHROPIC_API_KEY` and set `CORS_ORIGINS` to your web URL. The 1 GB disk keeps the SQLite database.
2. **Website on Vercel**: import the repo, set root directory `apps/web`, add `NEXT_PUBLIC_API_URL=https://<your-api>.onrender.com`.
3. **Mobile**: set `extra.apiUrl` in `apps/mobile/app.json`, then `npx eas build -p android --profile preview` for an APK, and `eas submit` for Play Store / App Store.

## Content and licensing
See `content/SOURCES.md`. Sample questions in `content/seed/` are original drafts marked `reviewed: 0`; have a doctor review them before real use. Do not commit copyrighted books or paid course material.

## Roadmap
Real accounts (login) and cloud database, doctor review workflow for questions, image-based questions, PYQ topic weightage from real data, push reminders for due cards, mock tests with timers.

Study support only, not medical advice.
