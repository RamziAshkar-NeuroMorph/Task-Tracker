# syntax=docker/dockerfile:1

# ---------- Stage 1: builder ----------
# Pinned to the 3.11 slim image (never python:latest) so rebuilds are reproducible.
FROM python:3.11-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

# Build dependencies into a self-contained virtualenv so the runtime stage
# never needs pip or a build toolchain.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copied on its own: dependency layers stay cached across source-only edits.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt


# ---------- Stage 2: runtime ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Unprivileged runtime user.
RUN useradd --create-home --shell /usr/sbin/nologin app

WORKDIR /srv

COPY --from=builder /opt/venv /opt/venv

# Only the importable application package. No tests, no frontend, no .env:
# configuration is supplied at run time via -e / --env-file, never baked in.
COPY --chown=app:app app/ ./app/

USER app

EXPOSE 8000

# Uses the stdlib so the slim image needs no curl/wget.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status == 200 else 1)"

# No --reload: the reloader is a development-only file watcher.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
