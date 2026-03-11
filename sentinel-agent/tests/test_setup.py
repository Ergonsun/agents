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
        "y",                             # setup email?
        "smtp.example.com",             # smtp host
        "587",                           # smtp port
        "user@example.com",             # username
        "password123",                   # password
        "sentinel@example.com",         # from
        "roger@example.com",            # to
    ])

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        with patch("builtins.input", lambda _="": next(inputs)):
            config = await run_first_time_setup(config_path)

        assert len(config.targets) == 2
        assert config.targets[0].name == "ADGA"
        assert config.signal.enabled is True
        assert config.email.enabled is True

        # Verify it was saved
        reloaded = load_config(config_path)
        assert reloaded is not None
        assert len(reloaded.targets) == 2


@pytest.mark.asyncio
async def test_first_time_setup_minimal() -> None:
    """Test setup with signal and email skipped."""
    inputs = iter([
        "MyApp",                         # target name
        "http://localhost:5000/health",  # target url
        "n",                             # add another?
        "n",                             # setup signal?
        "n",                             # setup email?
    ])

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.yaml"
        with patch("builtins.input", lambda _="": next(inputs)):
            config = await run_first_time_setup(config_path)

        assert len(config.targets) == 1
        assert config.signal.enabled is False
        assert config.email.enabled is False
