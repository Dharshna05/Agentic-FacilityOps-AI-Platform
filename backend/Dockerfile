# FacilityOps backend — FastAPI + scikit-learn/TensorFlow ML services.
FROM python:3.12-slim

WORKDIR /app

# build-essential: a couple of this project's deps (bcrypt, some numpy/
# pandas transitive deps) don't always ship a prebuilt wheel for every
# platform python:3.12-slim might run on (e.g. arm64) — without this,
# `pip install` silently falls back to compiling from source and fails
# with a confusing "gcc not found" error instead of a dependency error.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN mkdir -p /app/data

# Run as a non-root user — the base image defaults to root, which is an
# unnecessary privilege escalation surface for a process that only needs
# to read its own files and bind one port.
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Lets `docker compose ps` / orchestrators tell "container is running" apart
# from "app inside is actually serving requests" — hits the same /health
# route the frontend's connection-failed error message already points to.
HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# --workers is deliberately left at uvicorn's default (1): the ML model
# objects loaded per-worker are large (the TensorFlow occupancy CNN
# especially), so raising this without sizing container memory
# accordingly will OOM — see README's Docker section before changing this
# for a real multi-user deployment.
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
