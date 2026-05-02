# syntax=docker/dockerfile:1.6
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# pexpect spawns child processes; ensure a usable shell + common utilities
# for TUI applications under test.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        coreutils \
        ncurses-bin \
        procps \
        tini \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first for better layer caching
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# stdio-based MCP server — keep stdin open when running interactively
ENTRYPOINT ["/usr/bin/tini", "--", "python", "/app/server.py"]
