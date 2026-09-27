FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Build the backend app from its maintained dependency list and source tree.
COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY backend/ .

EXPOSE 8000

# A standalone IDE run uses SQLite; the full Compose stack supplies PostgreSQL.
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && gunicorn --bind 0.0.0.0:8000 -k uvicorn.workers.UvicornWorker app.main:app"]
