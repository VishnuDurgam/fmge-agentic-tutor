FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/app ./apps/api/app
COPY content ./content
ENV CONTENT_DIR=/app/content DB_PATH=/data/fmge.db
# Build the study library at image build time: download open-licence books, then index them
RUN python content/tools/fetch_open_books.py /tmp/books && cd apps/api && python -m app.ingest && rm -rf /tmp/books
EXPOSE 8000
WORKDIR /app/apps/api
CMD ["sh", "-c", "mkdir -p /data && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
