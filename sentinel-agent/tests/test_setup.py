# tests/test_setup.py
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from sentinel.config import load_config
from sentinel.setup import run_first_time_setup


@pytest.mark.asyncio
async def test_first_time_setup_full() -> None:
    """Test setup with all inputs provided."""
    inputs = iter([
        "ADGA",                          # target 1 name
        "http://localhost:8000/health",   # target 1 url
        "y",                             # add another?
        "Blacksmith",                    # target 2 name
        "http://localhost:3000/health",  # target 2 url
        "n",                             # add another?
        "y",                             # setup signal?
        "http://localhost:8080",         # signal api url
        "+1234567890",                   # signal phone
        "+0987654321",                   # signal recipient
        "y",                             # setup ntfy?
        "https://ntfy.sh",              # server url
        "test-topic",                    # topic
        "high",                          # priority
        "y",                             # setup slack?
        "https://hooks.slack.com/x",     # webhook url
        "#alerts",                       # channel
        "y",                             # setup github?
        "Ergonsun/adga",                 # repo
        "deploy.yml",                    # workflow
        "",                              # token (blank)
        "y",                             # setup hetzner?
        "hcloud_token",                  # token
        "adga-prod, blacksmith-prod",    # server names
    ])

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        with patch("builtins.input", lambda _="": next(inputs)):
            config = await run_first_time_setup(config_path)

        assert len(config.targets) == 2
        assert config.targets[0].name == "ADGA"
        assert config.signal.enabled is True
        assert config.ntfy.enabled is True
        assert config.slack.enabled is True
        assert config.github.enabled is True
        assert config.github.repo == "Ergonsun/adga"
        assert config.hetzner.enabled is True
        assert config.hetzner.server_names == ["adga-prod", "blacksmith-prod"]

        # Verify it was saved
        reloaded = load_config(config_path)
        assert reloaded is not None
        assert len(reloaded.targets) == 2


@pytest.mark.asyncio
async def test_first_time_setup_minimal() -> None:
    """Test setup with all optional monitors skipped."""
    inputs = iter([
        "MyApp",                         # target name
        "http://localhost:5000/health",  # target url
        "n",                             # add another?
        "n",                             # setup signal?
        "n",                             # setup ntfy?
        "n",                             # setup slack?
        "n",                             # setup github?
        "n",                             # setup hetzner?
    ])

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        with patch("builtins.input", lambda _="": next(inputs)):
            config = await run_first_time_setup(config_path)

        assert len(config.targets) == 1
        assert config.signal.enabled is False
        assert config.ntfy.enabled is False
        assert config.slack.enabled is False
        assert config.github.enabled is False
        assert config.hetzner.enabled is False
