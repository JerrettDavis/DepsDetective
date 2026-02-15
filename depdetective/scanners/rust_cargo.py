from __future__ import annotations

import re
import tomllib
from collections.abc import MutableMapping
from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.registry_clients import latest_crates_version
from depdetective.scanners.base import BaseScanner

FIRST_SEMVER = re.compile(r"(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)")
DEPENDENCY_KEYS = ("dependencies", "dev-dependencies", "build-dependencies")


def _extract_version(spec: str) -> str | None:
    match = FIRST_SEMVER.search(spec)
    if not match:
        return None
    return match.group(1)


def _iter_dependency_tables(doc: dict) -> list[tuple[str, MutableMapping]]:
    tables: list[tuple[str, MutableMapping]] = []
    for key in DEPENDENCY_KEYS:
        table = doc.get(key)
        if isinstance(table, MutableMapping):
            tables.append((key, table))

    workspace = doc.get("workspace")
    if isinstance(workspace, MutableMapping):
        table = workspace.get("dependencies")
        if isinstance(table, MutableMapping):
            tables.append(("workspace.dependencies", table))

    target = doc.get("target")
    if isinstance(target, MutableMapping):
        for target_name, target_table in target.items():
            if not isinstance(target_table, MutableMapping):
                continue
            for dep_key in DEPENDENCY_KEYS:
                table = target_table.get(dep_key)
                if isinstance(table, MutableMapping):
                    tables.append((f"target.{target_name}.{dep_key}", table))
    return tables


class RustCargoScanner(BaseScanner):
    ecosystem = "rust"

    def discover_files(self, repo_root: Path) -> list[Path]:
        return [
            path
            for path in repo_root.rglob("Cargo.toml")
            if ".git" not in path.parts and "target" not in path.parts
        ]

    def scan_file(self, file_path: Path, repo_root: Path) -> list[DependencyRecord]:
        payload = tomllib.loads(file_path.read_text(encoding="utf-8"))
        relative = str(file_path.relative_to(repo_root))
        records: list[DependencyRecord] = []

        for section, table in _iter_dependency_tables(payload):
            for dep_name, dep_spec in table.items():
                if isinstance(dep_spec, str):
                    spec = dep_spec
                elif isinstance(dep_spec, MutableMapping) and "version" in dep_spec:
                    spec = str(dep_spec["version"])
                else:
                    continue
                records.append(
                    DependencyRecord(
                        ecosystem=self.ecosystem,
                        name=str(dep_name),
                        file_path=relative,
                        current_spec=spec,
                        resolved_version=_extract_version(spec),
                        latest_version=latest_crates_version(str(dep_name)),
                        section=section,
                    )
                )
        return records

