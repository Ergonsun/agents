"""First-run interactive setup wizard."""

from pathlib import Path

from sentinel.config import (
    DEFAULT_CONFIG_PATH,
    EmailConfig,
    SentinelConfig,
    SignalConfig,
    TargetConfig,
    save_config,
)


def _ask(prompt: str, default: str = "") -> str:
    """Prompt user for input with optional default."""
    suffix = f" [{default}]" if default else ""
    result = input(f"  {prompt}{suffix}: ").strip()
    return result or default


def _ask_yn(prompt: str, default: bool = False) -> bool:
    """Prompt user for yes/no."""
    suffix = " [Y/n]" if default else " [y/N]"
    result = input(f"  {prompt}{suffix}: ").strip().lower()
    if not result:
        return default
    return result in ("y", "yes")


async def run_first_time_setup(
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> SentinelConfig:
    """Run interactive first-time setup. Returns the created config."""
    print("\n[Sentinel] No configuration found. Starting first-run setup...\n")
    print("─── Monitor Targets ───")

    targets: list[TargetConfig] = []
    while True:
        name = _ask("Service name (e.g., ADGA)")
        url = _ask("Health endpoint URL")
        targets.append(TargetConfig(name=name, url=url))
        if not _ask_yn("Add another target?"):
            break

    # Signal setup
    print("\n─── Signal Messaging ───")
    signal = SignalConfig()
    if _ask_yn("Set up Signal notifications?"):
        signal = SignalConfig(
            enabled=True,
            api_url=_ask("Signal-CLI REST API URL", "http://localhost:8080"),
            phone_number=_ask("Your Signal phone number (with country code)"),
            recipient=_ask("Alert recipient phone number"),
        )

    # Email setup
    print("\n─── Email Alerts ───")
    email = EmailConfig()
    if _ask_yn("Set up email notifications?"):
        email = EmailConfig(
            enabled=True,
            smtp_host=_ask("SMTP host"),
            smtp_port=int(_ask("SMTP port", "587")),
            username=_ask("SMTP username"),
            password=_ask("SMTP password"),
            from_addr=_ask("From address"),
            to_addr=_ask("To address"),
        )

    config = SentinelConfig(
        targets=targets,
        signal=signal,
        email=email,
    )
    save_config(config, config_path)
    print(f"\n[Sentinel] Configuration saved to {config_path}")
    return config
