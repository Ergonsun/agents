"""Configuration loading, validation, and persistence."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Self

import yaml

DEFAULT_POLL_INTERVAL = 300  # 5 minutes
DEFAULT_CONFIG_PATH = Path.home() / ".sentinel" / "config.yaml"


@dataclass(frozen=True, slots=True)
class TargetConfig:
    name: str
    url: str

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        return cls(name=data["name"], url=data["url"])

    def to_dict(self) -> dict:
        return {"name": self.name, "url": self.url}


@dataclass(frozen=True, slots=True)
class SignalConfig:
    enabled: bool = False
    api_url: str = ""
    phone_number: str = ""
    recipient: str = ""

    @classmethod
    def from_dict(cls, data: dict | None) -> Self:
        if not data or not data.get("enabled", False):
            return cls()
        return cls(
            enabled=True,
            api_url=data.get("api_url", ""),
            phone_number=data.get("phone_number", ""),
            recipient=data.get("recipient", ""),
        )

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "api_url": self.api_url,
            "phone_number": self.phone_number,
            "recipient": self.recipient,
        }


@dataclass(frozen=True, slots=True)
class NtfyConfig:
    enabled: bool = False
    server_url: str = "https://ntfy.sh"
    topic: str = ""
    priority: str = "high"

    @classmethod
    def from_dict(cls, data: dict | None) -> Self:
        if not data or not data.get("enabled", False):
            return cls()
        return cls(
            enabled=True,
            server_url=data.get("server_url", "https://ntfy.sh"),
            topic=data.get("topic", ""),
            priority=data.get("priority", "high"),
        )

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "server_url": self.server_url,
            "topic": self.topic,
            "priority": self.priority,
        }


@dataclass(frozen=True, slots=True)
class SlackConfig:
    """Slack webhook alerting — posts to a channel via incoming webhook."""
    enabled: bool = False
    webhook_url: str = ""
    channel: str = "#sentinel-alerts"

    @classmethod
    def from_dict(cls, data: dict | None) -> Self:
        if not data or not data.get("enabled", False):
            return cls()
        return cls(
            enabled=True,
            webhook_url=data.get("webhook_url", ""),
            channel=data.get("channel", "#sentinel-alerts"),
        )

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "webhook_url": self.webhook_url,
            "channel": self.channel,
        }


@dataclass(frozen=True, slots=True)
class GitHubConfig:
    """GitHub Actions workflow monitoring."""
    enabled: bool = False
    repo: str = ""  # e.g. "Ergonsun/adga"
    workflow: str = "deploy.yml"  # workflow file name
    token: str = ""  # GitHub personal access token

    @classmethod
    def from_dict(cls, data: dict | None) -> Self:
        if not data or not data.get("enabled", False):
            return cls()
        return cls(
            enabled=True,
            repo=data.get("repo", ""),
            workflow=data.get("workflow", "deploy.yml"),
            token=data.get("token", ""),
        )

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "repo": self.repo,
            "workflow": self.workflow,
            "token": self.token,
        }


@dataclass(frozen=True, slots=True)
class HetznerMonitorConfig:
    """Hetzner Cloud server status monitoring."""
    enabled: bool = False
    token: str = ""
    server_names: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict | None) -> Self:
        if not data or not data.get("enabled", False):
            return cls()
        return cls(
            enabled=True,
            token=data.get("token", ""),
            server_names=data.get("server_names", []),
        )

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "token": self.token,
            "server_names": self.server_names,
        }


@dataclass(frozen=True, slots=True)
class SentinelConfig:
    targets: list[TargetConfig]
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL
    signal: SignalConfig = field(default_factory=SignalConfig)
    ntfy: NtfyConfig = field(default_factory=NtfyConfig)
    slack: SlackConfig = field(default_factory=SlackConfig)
    github: GitHubConfig = field(default_factory=GitHubConfig)
    hetzner: HetznerMonitorConfig = field(default_factory=HetznerMonitorConfig)

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        targets = [TargetConfig.from_dict(t) for t in data.get("targets", [])]
        return cls(
            targets=targets,
            poll_interval_seconds=data.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL),
            signal=SignalConfig.from_dict(data.get("signal")),
            ntfy=NtfyConfig.from_dict(data.get("ntfy")),
            slack=SlackConfig.from_dict(data.get("slack")),
            github=GitHubConfig.from_dict(data.get("github")),
            hetzner=HetznerMonitorConfig.from_dict(data.get("hetzner")),
        )

    def to_dict(self) -> dict:
        return {
            "targets": [t.to_dict() for t in self.targets],
            "poll_interval_seconds": self.poll_interval_seconds,
            "signal": self.signal.to_dict(),
            "ntfy": self.ntfy.to_dict(),
            "slack": self.slack.to_dict(),
            "github": self.github.to_dict(),
            "hetzner": self.hetzner.to_dict(),
        }


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> SentinelConfig | None:
    """Load config from YAML file. Returns None if file doesn't exist."""
    if not path.exists():
        return None
    with open(path) as f:
        data = yaml.safe_load(f)
    return SentinelConfig.from_dict(data)


def save_config(config: SentinelConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    """Save config to YAML file, creating parent dirs if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False, sort_keys=False)
