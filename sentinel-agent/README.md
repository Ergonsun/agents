# Sentinel Agent

Lightweight async production monitoring agent with Signal messaging and email alerting.

## Features

- Polls service health endpoints every 5 minutes
- Alerts via Signal and/or email when services go down
- Responds to Signal messages with AI-powered health reports (Claude Haiku)
- Fixed-size health history (no memory leaks)
- Self-configuring first-run setup
- ~15MB idle memory footprint

## Quick Start

```bash
# Install
uv venv && uv pip install -e ".[dev]"

# Run (first time will prompt for configuration)
uv run sentinel

# Run tests
uv run pytest -v
```

## Requirements

- Python 3.12+
- signal-cli-rest-api (for Signal integration)
- Anthropic API key in `ANTHROPIC_API_KEY` env var (for AI health responses)

## Architecture

```
Sentinel Agent (asyncio single-process)
├── Health Poller (5m interval, aiohttp)
├── Signal Listener (30s poll inbox)
│   └── Claude Haiku for natural language responses
├── Alert Router (Signal + Email, dedup)
├── Config Store (~/.sentinel/config.yaml)
└── Health Ring Buffer (100 entries, ~10KB)
```
