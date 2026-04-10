# ---- Build Stage ----
FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install dependencies first for better layer caching
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and finalize install
COPY . .
RUN uv sync --frozen --no-dev

# ---- Runtime Stage ----
FROM python:3.12-slim AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder /app /app

# SECRET_KEY is required by Django settings loader even for collectstatic;
# the build-time dummy value is never used at runtime.
ARG SECRET_KEY=build-time-dummy-secret-key-not-used-in-production
ENV SECRET_KEY=${SECRET_KEY}
RUN python manage.py collectstatic --noinput
ENV SECRET_KEY=

EXPOSE 8000

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "60"]
