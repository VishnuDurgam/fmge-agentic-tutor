FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git tesseract-ocr && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/app ./apps/api/app
COPY content ./content
ENV CONTENT_DIR=/app/content DB_PATH=/data/fmge.db
# Optional private notes: set PRIVATE_REPO (owner/name) and PRIVATE_TOKEN in Render to pull them in. Never baked into git.
ARG PRIVATE_REPO=""
ARG PRIVATE_TOKEN=""
RUN if [ -n "$PRIVATE_REPO" ] && [ -n "$PRIVATE_TOKEN" ]; then \
      git clone --depth 1 "https://x-access-token:${PRIVATE_TOKEN}@github.com/${PRIVATE_REPO}.git" /tmp/priv \
      && mkdir -p content/raw/private && cp -r /tmp/priv/text/. content/raw/private/ ; \
      rm -rf /tmp/priv ; \
    fi
# Build the study library at image build time: download open-licence books, then index them
RUN python content/tools/fetch_open_books.py /tmp/books && cd apps/api && python -m app.ingest && rm -rf /tmp/books
EXPOSE 8000
WORKDIR /app/apps/api
CMD ["sh", "-c", "mkdir -p /data && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
