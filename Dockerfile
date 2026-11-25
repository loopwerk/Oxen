FROM ghcr.io/astral-sh/uv:0.13.9-trixie-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_INSTALL_DIR=/python \
    UV_PYTHON_PREFERENCE=only-managed

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python and the dependencies first, so this layer stays cached until pyproject.toml, uv.lock or .python-version change.
COPY .python-version pyproject.toml uv.lock ./
RUN uv python install && uv sync --locked --no-group dev --group prod --no-install-project

COPY . .

# Settings refuse to load without these outside DEBUG; building doesn't need the real ones.
RUN export SECRET_KEY=build SETUP_TOKEN=build \
    && uv run --no-sync ./manage.py tailwind build \
    && uv run --no-sync ./manage.py collectstatic --noinput \
    && rm -rf .django_tailwind_cli


# Final stage: just Python, the app with its virtualenv, and what WeasyPrint needs at runtime.
FROM debian:trixie-slim

# Pango for WeasyPrint, fonts for the PDFs (a slim image has none at all), and curl for the health check.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0 fonts-liberation curl \
    && rm -rf /var/lib/apt/lists/*

# Don't run as root
RUN groupadd --system --gid 999 app && useradd --system --gid 999 --uid 999 --home-dir /app app

COPY --from=builder /python /python
COPY --from=builder --chown=app:app /app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

WORKDIR /app
USER app
EXPOSE 8000

# Migrations need the real database, so they run on  start instead of during the build.
CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 2 --access-logfile -"]
