# Sentinel Agent

Lightweight async production monitoring agent for the AtelierLabs platform. Monitors service health, GitHub Actions deploys, and Hetzner Cloud infrastructure with multi-channel alerting.

## Features

- Polls service health endpoints every 5 minutes
- Monitors GitHub Actions deploy workflows (60s poll)
- Monitors Hetzner Cloud server status
- Alerts via Signal, ntfy, and/or Slack when issues detected
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
- signal-cli-rest-api (for Signal integration, optional)
- Anthropic API key in `ANTHROPIC_API_KEY` env var (for AI health responses)
- GitHub token (for private repo deploy monitoring, optional)
- Hetzner Cloud API token (for server monitoring, optional)

## Architecture

```
Sentinel Agent (asyncio single-process)
├── Health Poller (5m interval, aiohttp)
├── GitHub Actions Monitor (60s poll, deploy status)
├── Hetzner Monitor (5m poll, server status)
├── Signal Listener (30s poll inbox)
│   └── Claude Haiku for natural language responses
├── Alert Router (Signal + ntfy + Slack, dedup)
├── Config Store (~/.sentinel/config.yaml)
└── Health Ring Buffer (100 entries, ~10KB)
```

## Configuration

Config lives at `~/.sentinel/config.yaml`. Example:

```yaml
targets:
  - name: ADGA
    url: http://46.62.196.38:8000/health
  - name: Blacksmith
    url: http://46.62.216.88:9000/health

poll_interval_seconds: 300

slack:
  enabled: true
  webhook_url: https://hooks.slack.com/services/T00/B00/xxx
  channel: "#sentinel-alerts"

github:
  enabled: true
  repo: Ergonsun/adga
  workflow: deploy.yml
  token: ghp_xxx

hetzner:
  enabled: true
  token: hcloud_xxx
  server_names:
    - adga-prod
    - blacksmith-prod

signal:
  enabled: false
  api_url: ""
  phone_number: ""
  recipient: ""

ntfy:
  enabled: false
  server_url: https://ntfy.sh
  topic: ""
  priority: high
```
