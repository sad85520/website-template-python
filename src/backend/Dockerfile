# ---- Build Stage ----
FROM python:3.12-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

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
FROM python:3.12-slim-bookworm AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --system --no-create-home --shell /usr/sbin/nologin --uid 1000 appuser \
    && mkdir -p /app \
    && chown -R appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /app /app

# These vars are required by the settings loader at import time.
# Dummy values are used only during collectstatic and are cleared afterwards.
ARG SECRET_KEY=build-time-dummy-secret-key-not-used-in-production
ARG DB_PASSWORD=build-time-dummy
ARG JWT_SIGNING_KEY=build-time-dummy-jwt-signing-key-not-used-in-production
ARG ALLOWED_HOSTS=build-time-dummy
ENV SECRET_KEY=${SECRET_KEY} \
    DB_PASSWORD=${DB_PASSWORD} \
    JWT_SIGNING_KEY=${JWT_SIGNING_KEY} \
    ALLOWED_HOSTS=${ALLOWED_HOSTS}
RUN python manage.py collectstatic --noinput
ENV SECRET_KEY= \
    DB_PASSWORD= \
    JWT_SIGNING_KEY= \
    ALLOWED_HOSTS=

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health/', timeout=4).status == 200 else 1)"

CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-4} --timeout ${GUNICORN_TIMEOUT:-60}"]
