FROM python:3.13-slim

WORKDIR /app

# Minimal runtime libs for Pillow when a report PNG is rendered (not required at boot).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libjpeg62-turbo zlib1g libfreetype6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV PYTHONUNBUFFERED=1
# Cloud Run injects PORT; default 8000 for local docker runs.
ENV PORT=8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
