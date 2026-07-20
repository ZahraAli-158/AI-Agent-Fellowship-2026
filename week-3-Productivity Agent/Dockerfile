# Personal Productivity and Task Execution Agent — container image
FROM python:3.11-slim

WORKDIR /app

# System deps kept minimal; sqlite3 is bundled with Python's stdlib.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Persistent SQLite file lives here; mount a volume at /app/data in
# production if you need the database to survive container restarts
# (see README.md's "Deployment" section for platform-specific notes).
RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

CMD ["streamlit", "run", "app/main.py"]
