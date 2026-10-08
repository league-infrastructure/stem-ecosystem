# One-shot partner-scrape run: scrape -> enrich -> normalize -> export,
# with cache and data in the DigitalOcean Spaces bucket
# (s3://jtl-stem-ecosystem-scrape/{cache,data}). The container exits when
# the run finishes. See README.md in this directory.
#
# Build from the repo root (the build needs src/data/partners.json as well
# as scraper/):
#
#   docker build -f scraper/docker/Dockerfile -t partner-scrape .
#
# Secrets are NOT baked into the image; pass them at run time:
#
#   docker run --rm --ipc=host --env-file .env partner-scrape
#
# Base image ships Python plus Chromium and its OS libraries for
# headless (Playwright) fetching. Keep its tag in step with the
# playwright version pinned in scraper/uv.lock, or the playwright
# package will look for a browser build the image does not have.
FROM mcr.microsoft.com/playwright/python:v1.61.0-noble

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /usr/local/bin/uv

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
    PYTHONUNBUFFERED=1

# pwuser is the non-root user the Playwright image provides.
USER pwuser

# Extra arguments go straight to the CLI, e.g. `--source xplorstem`.
ENTRYPOINT ["partner-scrape"]
