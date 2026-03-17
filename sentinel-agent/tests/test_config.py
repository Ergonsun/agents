import tempfile
from pathlib import Path

import yaml

from sentinel.config import SentinelConfig, load_config, save_config


def test_load_config_from_file(sample_config: dict) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        yaml.dump(sample_config, f)
        path = Path(f.name)

    config = load_config(path)
    assert config.targets[0].name == "ADGA"
    assert config.targets[0].url == "http://localhost:8000/health"
    assert config.signal.enabled is True
    assert config.ntfy.enabled is True
    assert config.slack.enabled is True
    assert config.github.enabled is True
    assert config.github.repo == "Ergonsun/adga"
    assert config.hetzner.enabled is True
    assert config.hetzner.server_names == ["adga-prod", "blacksmith-prod"]
    assert config.poll_interval_seconds == 300
    path.unlink()


def test_load_config_missing_file() -> None:
    config = load_config(Path("/tmp/nonexistent_sentinel_config.yaml"))
    assert config is None


def test_save_and_reload(sample_config: dict) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "config.yaml"
        config = SentinelConfig.from_dict(sample_config)
        save_config(config, path)

        assert path.exists()
        reloaded = load_config(path)
        assert reloaded is not None
        assert reloaded.targets[0].name == config.targets[0].name
        assert reloaded.signal.phone_number == config.signal.phone_number
        assert reloaded.slack.webhook_url == config.slack.webhook_url
        assert reloaded.github.repo == config.github.repo
        assert reloaded.hetzner.token == config.hetzner.token


def test_config_defaults_disabled_channels() -> None:
    minimal = {
        "targets": [{"name": "Test", "url": "http://localhost/health"}],
    }
    config = SentinelConfig.from_dict(minimal)
    assert config.signal.enabled is False
    assert config.ntfy.enabled is False
    assert config.slack.enabled is False
    assert config.github.enabled is False
    assert config.hetzner.enabled is False
    assert config.poll_interval_seconds == 300
