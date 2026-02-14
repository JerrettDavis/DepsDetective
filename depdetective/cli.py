from __future__ import annotations

import argparse
import json
import sys

from depdetective.config import load_config
from depdetective.logging_utils import configure_logging
from depdetective.runner import run_bot


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DepDetective dependency automation bot.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_cmd = subparsers.add_parser("run", help="Run scanning + update workflow.")
    run_cmd.add_argument("--config", help="Path to depdetective YAML config file.")
    run_cmd.add_argument("--repo-url", help="Repository clone URL override.")
    run_cmd.add_argument("--base-branch", help="Base branch to track.")
    run_cmd.add_argument(
        "--provider",
        choices=["github", "gitlab", "azure_devops", "ado", "azure", "generic"],
        help="Provider type.",
    )
    run_cmd.add_argument("--provider-repo", help="Provider repo slug (e.g. OWNER/REPO).")
    run_cmd.add_argument("--provider-token-env", help="Token env var name override.")
    run_cmd.add_argument("--provider-host", help="Provider API host/base URL override.")
    run_cmd.add_argument("--dry-run", action="store_true", help="Plan updates without pushing/PR calls.")
    run_cmd.add_argument(
        "--ecosystem",
        action="append",
        help="Limit scanning to one or more ecosystems (repeatable). Use 'auto' to include auto-detected.",
    )
    run_cmd.add_argument("--auto-detect", dest="auto_detect", action="store_true", help="Enable auto detection.")
    run_cmd.add_argument(
        "--no-auto-detect",
        dest="auto_detect",
        action="store_false",
        help="Disable auto detection.",
    )
    run_cmd.set_defaults(auto_detect=None)
    run_cmd.add_argument("--report-path", help="Write JSON report to this path.")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)
    if args.command == "run":
        _run_command(args)
        return
    parser.print_help()
    sys.exit(2)


def _run_command(args: argparse.Namespace) -> None:
    overrides = _build_overrides(args)
    config = load_config(args.config, overrides=overrides)
    report = run_bot(config, report_path=args.report_path)
    print(
        json.dumps(
            {
                "dependencies_scanned": len(report.scanned_dependencies),
                "updates_applied": len(report.updates_applied),
                "vulnerabilities_found": report.vulnerabilities_count,
                "provider_pr_url": report.provider_pr_url,
                "pr_workflow_triggered": report.pr_workflow_triggered,
            }
        )
    )


def _build_overrides(args: argparse.Namespace) -> dict:
    raw: dict = {}
    if args.repo_url:
        raw.setdefault("repo", {})["url"] = args.repo_url
    if args.base_branch:
        raw.setdefault("repo", {})["base_branch"] = args.base_branch
    if args.provider:
        raw.setdefault("provider", {})["type"] = args.provider
    if args.provider_repo:
        raw.setdefault("provider", {})["repo"] = args.provider_repo
    if args.provider_token_env:
        raw.setdefault("provider", {})["token_env"] = args.provider_token_env
    if args.provider_host:
        raw.setdefault("provider", {})["host"] = args.provider_host
    if args.dry_run:
        raw.setdefault("automation", {})["dry_run"] = True
    if args.ecosystem:
        raw.setdefault("scan", {})["ecosystems"] = [str(item) for item in args.ecosystem]
    if args.auto_detect is not None:
        raw.setdefault("scan", {})["auto_detect"] = bool(args.auto_detect)
    return raw
