# Private setup for one student (paid course material)

Use this when the study material is a paid course (for example the DocTutorials workbooks) that must not be shared.
Rules: never commit the PDFs or the text made from them, and never deploy them to a public site.

1. Download the PDFs to your own computer (not into the repo folders that get committed).
2. Install Tesseract OCR, then `pip install -r apps/api/requirements-private.txt`.
3. OCR each PDF (the workbooks are scanned images, so plain text extraction returns nothing):
   `python content/tools/ocr_pdf.py "Physiology FMGE Workbook.pdf" "Physiology workbook (private)"`
   Output goes to `content/raw/local-private/`, which git and Docker ignore.
4. Index and run:
   `cd apps/api && pip install -r requirements.txt && python -m app.ingest && APP_PASSCODE=choose-a-code uvicorn app.main:app`
   `cd apps/web && npm install && npm run dev`  (open http://localhost:3000)
5. Phone on the same Wi-Fi: set `NEXT_PUBLIC_API_URL=http://<computer-ip>:8000` for the web app, or use the Expo app with the same address.

Keep it on the student's computer. If you later want it online for him only, host it on a private server with `APP_PASSCODE` set, upload the OCR text there directly (never via GitHub), and check the course's terms first.

## Making questions from the workbooks (stays on his computer)
The app writes MCQs and flashcards from whatever material is loaded, including the OCR text.
Material under `content/raw/local-private/` is marked private. By default it is only sent to a model running on the same computer, never to Gemini, Groq or other cloud services (free cloud tiers may use prompts to improve their products).

1. Install Ollama (ollama.com), then run `ollama pull llama3.1:8b` once.
2. Start the backend with `OLLAMA_MODEL=llama3.1:8b APP_PASSCODE=choose-a-code uvicorn app.main:app` (in `apps/api`).
3. In the website, open Practice, choose the workbook under "Make new questions from your study material", and press Generate. Or in a terminal: `python -m app.gen_cli "cardiac output" 10 --source "Physiology workbook (private)"`.
4. The questions appear in Practice and in Mock exams. They are drafts, so check them against the book, because small local models make mistakes.

To allow cloud models for private material anyway, set `ALLOW_CLOUD_LLM_FOR_PRIVATE=1`. Only do that if the course terms allow it.
