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
