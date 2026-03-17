"""First-run interactive setup wizard."""

from pathlib import Path

from sentinel.config import (
    DEFAULT_CONFIG_PATH,
    GitHubConfig,
    HetznerMonitorConfig,
    NtfyConfig,
    SentinelConfig,
    SignalConfig,
    SlackConfig,
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

    # ntfy setup
    print("\n─── Push Notifications (ntfy) ───")
    ntfy = NtfyConfig()
    if _ask_yn("Set up ntfy push notifications?"):
        ntfy = NtfyConfig(
            enabled=True,
            server_url=_ask("ntfy server URL", "https://ntfy.sh"),
            topic=_ask("ntfy topic (private, unique string)"),
            priority=_ask("Alert priority", "high"),
        )

    # Slack setup
    print("\n─── Slack Notifications ───")
    slack = SlackConfig()
    if _ask_yn("Set up Slack webhook notifications?"):
        slack = SlackConfig(
            enabled=True,
            webhook_url=_ask("Slack incoming webhook URL"),
            channel=_ask("Slack channel", "#sentinel-alerts"),
        )

    # GitHub Actions monitoring
    print("\n─── GitHub Actions Monitoring ───")
    github = GitHubConfig()
    if _ask_yn("Monitor GitHub Actions deploy workflows?"):
        github = GitHubConfig(
            enabled=True,
            repo=_ask("GitHub repo (e.g., Ergonsun/adga)"),
            workflow=_ask("Workflow filename", "deploy.yml"),
            token=_ask("GitHub token (for private repos, or leave blank)"),
        )

    # Hetzner monitoring
    print("\n─── Hetzner Cloud Monitoring ───")
    hetzner = HetznerMonitorConfig()
    if _ask_yn("Monitor Hetzner Cloud servers?"):
        token = _ask("Hetzner API token")
        server_names_raw = _ask("Server names to monitor (comma-separated, or blank for all)")
        server_names = [s.strip() for s in server_names_raw.split(",") if s.strip()] if server_names_raw else []
        hetzner = HetznerMonitorConfig(
            enabled=True,
            token=token,
            server_names=server_names,
        )

    config = SentinelConfig(
        targets=targets,
        signal=signal,
        ntfy=ntfy,
        slack=slack,
        github=github,
        hetzner=hetzner,
    )
    save_config(config, config_path)
    print(f"\n[Sentinel] Configuration saved to {config_path}")
    return config
