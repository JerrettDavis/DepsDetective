from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(slots=True)
class RepoConfig:
    url: str
    base_branch: str | None = None
    clone_dir: str | None = None


@dataclass(slots=True)
class ProviderConfig:
    type: str = "generic"
    repo: str | None = None
    token_env: str | None = None
    host: str | None = None


@dataclass(slots=True)
class ScanConfig:
    ecosystems: list[str] = field(default_factory=list)
    auto_detect: bool = True
    include_vulnerabilities: bool = True


@dataclass(slots=True)
class UpdateConfig:
    enabled: bool = True
    max_updates: int = 50


@dataclass(slots=True)
class AutomationConfig:
    branch_name: str = "depdetective/autoupdate"
    pr_title: str = "chore(deps): automated dependency updates"
    pr_body_template: str | None = None
    labels: list[str] = field(default_factory=lambda: ["dependencies"])
    rebase_existing: bool = True
    dry_run: bool = False


@dataclass(slots=True)
class HookConfig:
    before_scan: list[str] = field(default_factory=list)
    after_scan: list[str] = field(default_factory=list)
    before_update: list[str] = field(default_factory=list)
    after_update: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DepDetectiveConfig:
    repo: RepoConfig
    provider: ProviderConfig = field(default_factory=ProviderConfig)
    scan: ScanConfig = field(default_factory=ScanConfig)
    update: UpdateConfig = field(default_factory=UpdateConfig)
    automation: AutomationConfig = field(default_factory=AutomationConfig)
    hooks: HookConfig = field(default_factory=HookConfig)


def _coerce_repo(data: dict) -> RepoConfig:
    if "url" not in data:
        raise ValueError("repo.url is required")
    return RepoConfig(
        url=str(data["url"]),
        base_branch=str(data["base_branch"]) if data.get("base_branch") else None,
        clone_dir=data.get("clone_dir"),
    )


def _coerce_provider(data: dict) -> ProviderConfig:
    return ProviderConfig(
        type=str(data.get("type", "generic")),
        repo=data.get("repo"),
        token_env=data.get("token_env"),
        host=data.get("host"),
    )


def _coerce_scan(data: dict) -> ScanConfig:
    ecosystems = data.get("ecosystems", [])
    if ecosystems is None:
        ecosystems = []
    if not isinstance(ecosystems, list):
        raise ValueError("scan.ecosystems must be a list")
    auto_detect = bool(data.get("auto_detect", True))
    if not auto_detect and not ecosystems:
        raise ValueError("scan.ecosystems cannot be empty when scan.auto_detect is false")
    return ScanConfig(
        ecosystems=[str(item) for item in ecosystems],
        auto_detect=auto_detect,
        include_vulnerabilities=bool(data.get("include_vulnerabilities", True)),
    )


def _coerce_update(data: dict) -> UpdateConfig:
    max_updates = int(data.get("max_updates", 50))
    if max_updates < 1:
        raise ValueError("update.max_updates must be >= 1")
    return UpdateConfig(enabled=bool(data.get("enabled", True)), max_updates=max_updates)


def _coerce_automation(data: dict) -> AutomationConfig:
    labels = data.get("labels", ["dependencies"])
    if not isinstance(labels, list):
        raise ValueError("automation.labels must be a list")
    return AutomationConfig(
        branch_name=str(data.get("branch_name", "depdetective/autoupdate")),
        pr_title=str(data.get("pr_title", "chore(deps): automated dependency updates")),
        pr_body_template=data.get("pr_body_template"),
        labels=[str(label) for label in labels],
        rebase_existing=bool(data.get("rebase_existing", True)),
        dry_run=bool(data.get("dry_run", False)),
    )


def _coerce_hooks(data: dict) -> HookConfig:
    return HookConfig(
        before_scan=_coerce_hook_list(data.get("before_scan", []), "hooks.before_scan"),
        after_scan=_coerce_hook_list(data.get("after_scan", []), "hooks.after_scan"),
        before_update=_coerce_hook_list(data.get("before_update", []), "hooks.before_update"),
        after_update=_coerce_hook_list(data.get("after_update", []), "hooks.after_update"),
    )


def _coerce_hook_list(value: object, key: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list of shell commands")
    return [str(command) for command in value if str(command).strip()]


def load_config(config_path: str | None, overrides: dict | None = None) -> DepDetectiveConfig:
    raw: dict = {}
    if config_path:
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")
        with config_file.open("r", encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}

    overrides = overrides or {}
    raw = _merge_dicts(raw, overrides)

    if "repo" not in raw:
        raise ValueError("repo block is required")

    return DepDetectiveConfig(
        repo=_coerce_repo(raw["repo"]),
        provider=_coerce_provider(raw.get("provider", {})),
        scan=_coerce_scan(raw.get("scan", {})),
        update=_coerce_update(raw.get("update", {})),
        automation=_coerce_automation(raw.get("automation", {})),
        hooks=_coerce_hooks(raw.get("hooks", {})),
    )


def _merge_dicts(left: dict, right: dict) -> dict:
    merged = dict(left)
    for key, value in right.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _merge_dicts(merged[key], value)
            continue
        merged[key] = value
    return merged
