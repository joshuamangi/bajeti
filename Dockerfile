# Pinned by digest (multi-arch index, covers arm64 for the Pi). To update: pick a newer
# python:3.11-slim, read its digest with `docker buildx imagetools inspect`, change it here in a PR.
ARG PYTHON_IMAGE=python:3.11-slim@sha256:cce12316475d7d56d605f76e1d811d0dc4e7227f2d4afd29951521264f504ff8

# ---- build stage: compilers and headers live only here ----
FROM ${PYTHON_IMAGE} AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- final stage ----
FROM ${PYTHON_IMAGE}

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

COPY --from=build /opt/venv /opt/venv

# Run as a non-root user. APP_UID must match the owner of ./data on the Pi
# (check with `id -u` there), so the SQLite file and its journal stay writable.
ARG APP_UID=1000
RUN useradd --uid ${APP_UID} --create-home --shell /usr/sbin/nologin bajeti

# Copy entire app including built frontend
COPY --chown=bajeti:bajeti . .

USER bajeti

EXPOSE 8000

# Migrates (under a lock), then starts the server.
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
