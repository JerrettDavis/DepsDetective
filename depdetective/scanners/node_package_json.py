from __future__ import annotations

import json
import re
from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.registry_clients import latest_npm_version
from depdetective.scanners.base import BaseScanner

FIRST_VERSION = re.compile(r"(\d+\.\d+\.\d+)")


def _extract_version(spec: str) -> str | None:
    match = FIRST_VERSION.search(spec)
    if not match:
        return None
    return match.group(1)


class NodePackageScanner(BaseScanner):
    ecosystem = "node"

    def discover_files(self, repo_root: Path) -> list[Path]:
        return [
            path
            for path in repo_root.rglob("package.json")
            if "node_modules" not in path.parts and ".git" not in path.parts
        ]

    def scan_file(self, file_path: Path, repo_root: Path) -> list[DependencyRecord]:
        relative = str(file_path.relative_to(repo_root))
        payload = json.loads(file_path.read_text(encoding="utf-8"))
        records: list[DependencyRecord] = []
        for section in ("dependencies", "devDependencies"):
            deps = payload.get(section, {})
            if not isinstance(deps, dict):
                continue
            for name, spec in deps.items():
                resolved = _extract_version(str(spec))
                latest = latest_npm_version(name)
                records.append(
                    DependencyRecord(
                        ecosystem=self.ecosystem,
                        name=name,
                        file_path=relative,
                        current_spec=str(spec),
                        resolved_version=resolved,
                        latest_version=latest,
                        section=section,
                    )
                )
        return records

