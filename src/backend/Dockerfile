# ---- Build Stage ----
FROM python:3.14-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.26 /uv /uvx /bin/

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
FROM python:3.14-slim-bookworm AS runtime

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=config.settings.production \
    PATH="/app/.venv/bin:$PATH"

RUN useradd --system --no-create-home --shell /usr/sbin/nologin --uid 1000 appuser \
    && mkdir -p /app \
    && chown -R appuser:appuser /app

COPY --from=builder --chown=appuser:appuser /app /app

# These vars are required by the settings loader at import time (production.py
# does fail-fast on each one). Dummy values are used only during collectstatic
# and are cleared afterwards; the runtime container will be started with the
# real values from k8s Secret / ConfigMap.
# REDIS_URL: production.py raises ImproperlyConfigured when unset (DRF throttling
# would otherwise silently degrade to per-pod LocMemCache under HPA scale-out);
# the dummy URL below satisfies the import-time check without opening any socket
# — collectstatic does not touch the cache backend.
ARG SECRET_KEY=build-time-dummy-secret-key-not-used-in-production
ARG DB_PASSWORD=build-time-dummy
ARG JWT_SIGNING_KEY=build-time-dummy-jwt-signing-key-not-used-in-production
ARG ALLOWED_HOSTS=build-time-dummy
ARG REDIS_URL=redis://build-time-dummy:6379/0
ENV SECRET_KEY=${SECRET_KEY} \
    DB_PASSWORD=${DB_PASSWORD} \
    JWT_SIGNING_KEY=${JWT_SIGNING_KEY} \
    ALLOWED_HOSTS=${ALLOWED_HOSTS} \
    REDIS_URL=${REDIS_URL}
RUN python manage.py collectstatic --noinput
ENV SECRET_KEY= \
    DB_PASSWORD= \
    JWT_SIGNING_KEY= \
    ALLOWED_HOSTS= \
    REDIS_URL=

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health/', timeout=4).status == 200 else 1)"

CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-4} --timeout ${GUNICORN_TIMEOUT:-60}"]
