from __future__ import annotations

import json
import logging
import os
import tempfile
from urllib.parse import quote, urlsplit, urlunsplit
from uuid import uuid4
from pathlib import Path

from depdetective.config import DepDetectiveConfig
from depdetective.gitops import GitRepo
from depdetective.hooks import run_hook_commands
from depdetective.models import DependencyRecord, RunReport, UpdateAction
from depdetective.providers import build_provider
from depdetective.scanners import SCANNER_PLUGINS, known_ecosystems
from depdetective.security import enrich_vulnerabilities
from depdetective.updaters import UPDATER_PLUGINS

LOGGER = logging.getLogger(__name__)


def run_bot(config: DepDetectiveConfig, report_path: str | None = None) -> RunReport:
    root = _resolve_clone_dir(config)
    clone_url = _build_clone_url(config)
    base_branch = _resolve_base_branch(config, clone_url)
    repo = GitRepo.clone(clone_url, root, base_branch)
    repo.configure_identity()
    repo.create_or_reset_branch(config.automation.branch_name, base_branch)

    run_hook_commands(config.hooks.before_scan, cwd=root, stage_name="before_scan")

    deps = _scan_dependencies(root, config.scan.ecosystems, config.scan.auto_detect)
    run_hook_commands(config.hooks.after_scan, cwd=root, stage_name="after_scan")

    if config.scan.include_vulnerabilities:
        enrich_vulnerabilities(deps)

    report = RunReport(scanned_dependencies=deps)
    if not config.update.enabled:
        _write_report(report, report_path)
        return report

    run_hook_commands(config.hooks.before_update, cwd=root, stage_name="before_update")
    updates = _apply_updates(root, deps, config.update.max_updates)
    run_hook_commands(config.hooks.after_update, cwd=root, stage_name="after_update")

    report.updates_applied = updates
    if updates and repo.has_changes():
        report.pr_workflow_triggered = True
        if config.automation.dry_run:
            LOGGER.info(
                "Dry-run enabled: would commit, push '%s', and create/update PR/MR.",
                config.automation.branch_name,
            )
        else:
            repo.commit_all(_build_commit_message(updates))
            repo.push(config.automation.branch_name)
            provider = build_provider(
                config.provider.type,
                config.provider.repo,
                config.provider.token_env,
                host=config.provider.host,
                repo_url=config.repo.url,
            )
            pr_body = _build_pr_body(report)
            report.provider_pr_url = provider.open_or_update_pr(
                source_branch=config.automation.branch_name,
                target_branch=base_branch,
                title=config.automation.pr_title,
                body=pr_body,
                labels=config.automation.labels,
            )
    else:
        LOGGER.info("No updates to apply.")

    _write_report(report, report_path)
    return report


def _resolve_clone_dir(config: DepDetectiveConfig) -> Path:
    if config.repo.clone_dir:
        root_base = Path(config.repo.clone_dir).resolve()
        root_base.mkdir(parents=True, exist_ok=True)
        root = root_base / f"run-{uuid4().hex}"
        root.mkdir(parents=True, exist_ok=True)
        return root
    temp_dir = tempfile.mkdtemp(prefix="depdetective-")
    return Path(temp_dir)


def _scan_dependencies(
    repo_root: Path,
    ecosystems: list[str],
    auto_detect: bool,
) -> list[DependencyRecord]:
    discovered: list[tuple[object, list[Path]]] = []
    detected_ecosystems: set[str] = set()
    for scanner_cls in SCANNER_PLUGINS:
        scanner = scanner_cls()
        files = scanner.discover_files(repo_root)
        discovered.append((scanner, files))
        if files:
            detected_ecosystems.add(scanner.ecosystem)

    enabled_ecosystems = _resolve_enabled_ecosystems(
        ecosystems=ecosystems,
        auto_detect=auto_detect,
        detected=detected_ecosystems,
    )
    LOGGER.info("Scanning ecosystems: %s", ", ".join(enabled_ecosystems) if enabled_ecosystems else "(none)")

    records: list[DependencyRecord] = []
    for scanner, files in discovered:
        if scanner.ecosystem not in enabled_ecosystems:
            continue
        for file_path in files:
            records.extend(scanner.scan_file(file_path, repo_root))
    return records


def _resolve_enabled_ecosystems(
    ecosystems: list[str],
    auto_detect: bool,
    detected: set[str],
) -> list[str]:
    known = known_ecosystems()
    requested: list[str] = []
    explicit_auto = False
    for ecosystem in ecosystems:
        lowered = ecosystem.lower()
        if lowered == "auto":
            explicit_auto = True
            continue
        if lowered not in known:
            LOGGER.warning("Unknown ecosystem '%s' requested; skipping.", ecosystem)
            continue
        if lowered not in requested:
            requested.append(lowered)

    enabled = list(requested)
    if auto_detect or explicit_auto or not enabled:
        for ecosystem in sorted(detected):
            if ecosystem not in enabled:
                enabled.append(ecosystem)
    return enabled


def _apply_updates(
    repo_root: Path,
    dependencies: list[DependencyRecord],
    max_updates: int,
) -> list[UpdateAction]:
    changes: list[UpdateAction] = []
    ecosystems_with_candidates = {dep.ecosystem for dep in dependencies if dep.update_available}
    for updater_cls in UPDATER_PLUGINS:
        updater = updater_cls()
        if updater.ecosystem not in ecosystems_with_candidates:
            continue
        remaining = max(0, max_updates - len(changes))
        if remaining == 0:
            break
        applied = updater.apply_updates(repo_root, dependencies, remaining)
        changes.extend(applied)
    return changes


def _build_commit_message(updates: list[UpdateAction]) -> str:
    count = len(updates)
    if count == 1:
        only = updates[0]
        return f"chore(deps): bump {only.dependency} to {only.latest_version}"
    return f"chore(deps): update {count} dependencies"


def _build_pr_body(report: RunReport) -> str:
    lines = [
        "Automated dependency update generated by DepDetective.",
        "",
        "## Updated dependencies",
    ]
    if not report.updates_applied:
        lines.append("- No dependency changes were required.")
    else:
        for change in report.updates_applied:
            lines.append(
                f"- `{change.dependency}` in `{change.file_path}`: `{change.old_spec}` -> `{change.new_spec}`"
            )
    lines.extend(["", "## Vulnerabilities detected"])
    if report.vulnerabilities_count == 0:
        lines.append("- None detected in pinned versions scanned via OSV.")
    else:
        for dep in report.scanned_dependencies:
            for vuln in dep.vulnerabilities:
                lines.append(
                    f"- `{dep.name}` ({dep.file_path}) `{vuln.vuln_id}`"
                    + (f": {vuln.summary}" if vuln.summary else "")
                )
    return "\n".join(lines)


def _write_report(report: RunReport, report_path: str | None) -> None:
    if not report_path:
        return
    payload = {
        "scanned_dependencies": [
            {
                "ecosystem": dep.ecosystem,
                "name": dep.name,
                "file_path": dep.file_path,
                "current_spec": dep.current_spec,
                "resolved_version": dep.resolved_version,
                "latest_version": dep.latest_version,
                "update_available": dep.update_available,
                "vulnerabilities": [
                    {
                        "source": vuln.source,
                        "id": vuln.vuln_id,
                        "summary": vuln.summary,
                        "severity": vuln.severity,
                        "reference": vuln.reference,
                    }
                    for vuln in dep.vulnerabilities
                ],
            }
            for dep in report.scanned_dependencies
        ],
        "updates_applied": [
            {
                "ecosystem": upd.ecosystem,
                "file_path": upd.file_path,
                "dependency": upd.dependency,
                "old_spec": upd.old_spec,
                "new_spec": upd.new_spec,
                "latest_version": upd.latest_version,
            }
            for upd in report.updates_applied
        ],
        "provider_pr_url": report.provider_pr_url,
        "pr_workflow_triggered": report.pr_workflow_triggered,
    }
    Path(report_path).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_clone_url(config: DepDetectiveConfig) -> str:
    repo_url = config.repo.url
    provider_type = config.provider.type.lower()
    token_env = config.provider.token_env
    if provider_type == "github":
        token = os.getenv(token_env or "GITHUB_TOKEN")
        if token and repo_url.startswith("https://"):
            return _inject_credentials(
                repo_url,
                username="x-access-token",
                password=token,
            )
    if provider_type == "gitlab":
        token = os.getenv(token_env or "GITLAB_TOKEN")
        if token and repo_url.startswith("https://"):
            return _inject_credentials(
                repo_url,
                username="oauth2",
                password=token,
            )
    if provider_type in {"azure_devops", "ado", "azure"}:
        token = os.getenv(token_env or "AZURE_DEVOPS_TOKEN") or os.getenv("SYSTEM_ACCESSTOKEN")
        if token and repo_url.startswith("https://"):
            username = os.getenv("AZURE_DEVOPS_USER", "build")
            return _inject_credentials(repo_url, username=username, password=token)
    return repo_url


def _resolve_base_branch(config: DepDetectiveConfig, clone_url: str) -> str:
    if config.repo.base_branch:
        return config.repo.base_branch
    return GitRepo.detect_default_branch(clone_url)


def _inject_credentials(repo_url: str, username: str, password: str) -> str:
    parsed = urlsplit(repo_url)
    if parsed.scheme not in {"http", "https"}:
        return repo_url
    if "@" in parsed.netloc:
        return repo_url
    encoded_user = quote(username, safe="")
    encoded_pass = quote(password, safe="")
    netloc = f"{encoded_user}:{encoded_pass}@{parsed.netloc}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
