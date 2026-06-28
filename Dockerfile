FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Instala dependencias
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        "fastapi>=0.111" \
        "uvicorn[standard]>=0.30" \
        "gunicorn>=22.0" \
        "sqlalchemy>=2.0" \
        "alembic>=1.13" \
        "psycopg[binary]>=3.2" \
        "pydantic>=2.7" \
        "pydantic-settings>=2.3" \
        "redis>=5.0" \
        "celery>=5.4" \
        "pyjwt>=2.8" \
        "bcrypt>=4.1"

# Copia o codigo e instala o pacote local (sem baixar deps novamente)
COPY app ./app
COPY db ./db
COPY scripts ./scripts
RUN pip install --no-cache-dir --no-deps -e .

EXPOSE 8000

CMD ["sh", "-c", "python scripts/init_db.py && exec gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w 2 -b 0.0.0.0:${PORT:-8000}"]
