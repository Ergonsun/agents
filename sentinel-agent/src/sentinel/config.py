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
class EmailConfig:
    enabled: bool = False
    smtp_host: str = ""
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_addr: str = ""
    to_addr: str = ""

    @classmethod
    def from_dict(cls, data: dict | None) -> Self:
        if not data or not data.get("enabled", False):
            return cls()
        return cls(
            enabled=True,
            smtp_host=data.get("smtp_host", ""),
            smtp_port=data.get("smtp_port", 587),
            username=data.get("username", ""),
            password=data.get("password", ""),
            from_addr=data.get("from_addr", ""),
            to_addr=data.get("to_addr", ""),
        )

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "smtp_host": self.smtp_host,
            "smtp_port": self.smtp_port,
            "username": self.username,
            "password": self.password,
            "from_addr": self.from_addr,
            "to_addr": self.to_addr,
        }


@dataclass(frozen=True, slots=True)
class SentinelConfig:
    targets: list[TargetConfig]
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL
    signal: SignalConfig = field(default_factory=SignalConfig)
    email: EmailConfig = field(default_factory=EmailConfig)

    @classmethod
    def from_dict(cls, data: dict) -> Self:
        targets = [TargetConfig.from_dict(t) for t in data["targets"]]
        return cls(
            targets=targets,
            poll_interval_seconds=data.get("poll_interval_seconds", DEFAULT_POLL_INTERVAL),
            signal=SignalConfig.from_dict(data.get("signal")),
            email=EmailConfig.from_dict(data.get("email")),
        )

    def to_dict(self) -> dict:
        return {
            "targets": [t.to_dict() for t in self.targets],
            "poll_interval_seconds": self.poll_interval_seconds,
            "signal": self.signal.to_dict(),
            "email": self.email.to_dict(),
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
