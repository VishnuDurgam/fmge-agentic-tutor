FROM python:3.12-slim
WORKDIR /app
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/app ./apps/api/app
COPY content ./content
ENV CONTENT_DIR=/app/content DB_PATH=/data/fmge.db
EXPOSE 8000
WORKDIR /app/apps/api
CMD ["sh", "-c", "mkdir -p /data && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
