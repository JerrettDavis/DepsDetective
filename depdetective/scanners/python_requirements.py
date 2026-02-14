from __future__ import annotations

import re
from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.registry_clients import latest_pypi_version
from depdetective.scanners.base import BaseScanner

REQ_LINE = re.compile(r"^\s*([A-Za-z0-9_.-]+)\s*([=<>!~]{1,2})\s*([^\s;]+)")


def _extract_resolved_version(operator: str, version: str) -> str | None:
    if operator == "==":
        return version
    return None


class PythonRequirementsScanner(BaseScanner):
    ecosystem = "python"

    def discover_files(self, repo_root: Path) -> list[Path]:
        return [
            path
            for path in repo_root.rglob("requirements*.txt")
            if ".git" not in path.parts and ".venv" not in path.parts
        ]

    def scan_file(self, file_path: Path, repo_root: Path) -> list[DependencyRecord]:
        relative = str(file_path.relative_to(repo_root))
        records: list[DependencyRecord] = []
        for line in file_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                continue
            match = REQ_LINE.match(stripped)
            if not match:
                continue
            name, operator, version = match.groups()
            resolved = _extract_resolved_version(operator, version)
            latest = latest_pypi_version(name)
            records.append(
                DependencyRecord(
                    ecosystem=self.ecosystem,
                    name=name,
                    file_path=relative,
                    current_spec=f"{operator}{version}",
                    resolved_version=resolved,
                    latest_version=latest,
                )
            )
        return records

