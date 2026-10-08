# partner-scrape container with a built-in scheduler (supercronic).
# Cache and data live in the DigitalOcean Spaces bucket
# (s3://jtl-stem-ecosystem-scrape/{cache,data}). By default the container
# stays up and runs the jobs in crontab (America/Los_Angeles); any other
# arguments are passed to partner-scrape for a one-shot run. See README.md
# in this directory.
#
# Build from the repo root (the build needs src/data/partners.json as well
# as scraper/):
#
#   docker build -f scraper/docker/Dockerfile -t partner-scrape .
#
# Secrets are NOT baked into the image; pass them at run time as a bundle
# built by make-secrets.sh:
#
#   docker run -d --ipc=host -e SCRAPER_SECRETS_B64=... partner-scrape
#   docker exec <container> run-job directory      # run a job now
#   docker run --rm --ipc=host -e SCRAPER_SECRETS_B64=... partner-scrape --source xplorstem
#
# Base image ships Python plus Chromium and its OS libraries for
# headless (Playwright) fetching. Keep its tag in step with the
# playwright version pinned in scraper/uv.lock, or the playwright
# package will look for a browser build the image does not have.
FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

# Scheduler: supercronic, pinned by version and sha256 per architecture.
# tzdata is needed for CRON_TZ=America/Los_Angeles.
ARG TARGETARCH
ARG SUPERCRONIC_VERSION=v0.2.49
ARG SUPERCRONIC_SHA256_AMD64=a53ae236602c7338aba3fbaff40bda6300eae3b9fedb8261eb06cfe3724430c1
ARG SUPERCRONIC_SHA256_ARM64=02aa0cb229ba09050cba6638059dadb9eedc2276632ea43d6a57a2f8c1629dd5
RUN set -eux; \
    case "${TARGETARCH}" in \
      amd64) sha="${SUPERCRONIC_SHA256_AMD64}" ;; \
      arm64) sha="${SUPERCRONIC_SHA256_ARM64}" ;; \
      *) echo "unsupported arch: ${TARGETARCH}" >&2; exit 1 ;; \
    esac; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl tzdata; \
    curl -fsSL -o /usr/local/bin/supercronic \
      "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH}"; \
    echo "${sha}  /usr/local/bin/supercronic" | sha256sum -c -; \
    chmod 0755 /usr/local/bin/supercronic; \
    rm -rf /var/lib/apt/lists/*

# Use the image's Python rather than downloading one; install into a
# venv outside the source tree and put it on PATH.
ENV UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app

# Dependencies first so source edits don't invalidate this layer.
COPY scraper/pyproject.toml scraper/uv.lock ./
RUN uv sync --locked --no-dev --extra headless --no-install-project

# The wheel build force-includes docs/data-schema.md (see pyproject.toml).
COPY scraper/partner_scrape ./partner_scrape
COPY scraper/docs/data-schema.md ./docs/data-schema.md
RUN uv sync --locked --no-dev --extra headless --no-editable

# The curated partner roster is read from $SITE_DIR/src/data/partners.json.
# Nothing is written to SITE_DIR; all output goes to the data bucket.
COPY src/data/partners.json /site/src/data/partners.json

# Non-secret defaults; override with -e or --env-file. The cache and data
# locations default to the bucket in partner_scrape/config.py.
ENV SITE_DIR=/site \
    DO_SPACES_ENDPOINT=https://sfo3.digitaloceanspaces.com \
    TZ=America/Los_Angeles \
    PYTHONUNBUFFERED=1

# Scripts live together on PATH (run-job locates load-secrets beside itself).
COPY scraper/docker/entrypoint.sh scraper/docker/run-job scraper/docker/load-secrets scraper/docker/crontab /usr/local/bin/
RUN chmod 0755 /usr/local/bin/entrypoint.sh /usr/local/bin/run-job

# pwuser is the non-root user the Playwright image provides.
USER pwuser

# No args or `cron`: scheduler. `run-job JOB`: one job. Other args go
# straight to the CLI, e.g. `--source xplorstem`.
ENTRYPOINT ["entrypoint.sh"]
