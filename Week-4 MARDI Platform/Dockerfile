FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
ENV LLM_MODE=auto
ENV AUTO_APPROVE_CHECKPOINTS=false
ENV PORT=8000

EXPOSE 8000

# Default: serve the FastAPI app (what Render/Railway/any host needs).
# $PORT is respected if the platform injects one (Render, Railway, Heroku
# all do); falls back to 8000 for local `docker run`.
#
# To run the CLI instead inside the same image:
#   docker run --rm -it <image> python -m app.main --auto "your request"
CMD ["sh", "-c", "python -m uvicorn app.api:app --host 0.0.0.0 --port ${PORT}"]
