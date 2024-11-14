FROM python:3.12-slim AS builder

ENV POETRY_VERSION=1.8.4 \
    POETRY_VIRTUALENVS_IN_PROJECT=true

RUN apt update \
    && apt install -y \
    pipx; \
    pipx ensurepath

RUN pipx install poetry==${POETRY_VERSION}

RUN pipx run poetry --version

WORKDIR /build

COPY poetry.lock pyproject.toml ./
COPY maps_backend ./maps_backend

RUN touch README.md; \
    pipx run poetry install --without dev

FROM python:3.12-slim

ENV PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1

COPY --from=builder /build /app

WORKDIR /app

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "maps_backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
