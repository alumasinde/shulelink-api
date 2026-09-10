FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN groupadd --system --gid 10001 shulelink \
    && useradd --system --uid 10001 --gid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin shulelink

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The migration runner reads raw SQL from /app/database/migrations.
COPY app ./app
COPY database ./database
COPY scripts ./scripts

RUN chown -R 10001:10001 /app
USER 10001:10001

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
