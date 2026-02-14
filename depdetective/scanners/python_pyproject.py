from __future__ import annotations

import re
import tomllib
from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.registry_clients import latest_pypi_version
from depdetective.scanners.base import BaseScanner

PEP508_NAME = re.compile(r"^\s*([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?")
PEP508_PINNED = re.compile(r"^\s*[A-Za-z0-9_.-]+(?:\[[^\]]+\])?\s*==\s*([^\s;,@]+)")
FIRST_SEMVER = re.compile(r"(\d+\.\d+\.\d+)")


def _first_semver(spec: str) -> str | None:
    match = FIRST_SEMVER.search(spec)
    if not match:
        return None
    return match.group(1)


def _parse_pep508_entry(entry: str) -> tuple[str | None, str, str | None]:
    name_match = PEP508_NAME.match(entry)
    if not name_match:
        return None, entry.strip(), None
    name = name_match.group(1)
    pinned = PEP508_PINNED.match(entry)
    if pinned:
        version = pinned.group(1)
        return name, f"=={version}", version
    rest = entry[name_match.end() :].strip()
    return name, rest, None


class PythonPyprojectScanner(BaseScanner):
    ecosystem = "python"

    def discover_files(self, repo_root: Path) -> list[Path]:
        return [
            path
            for path in repo_root.rglob("pyproject.toml")
            if ".git" not in path.parts and ".venv" not in path.parts and "node_modules" not in path.parts
        ]

    def scan_file(self, file_path: Path, repo_root: Path) -> list[DependencyRecord]:
        payload = tomllib.loads(file_path.read_text(encoding="utf-8"))
        relative = str(file_path.relative_to(repo_root))
        records: list[DependencyRecord] = []

        project = payload.get("project", {})
        for dep in project.get("dependencies", []):
            if not isinstance(dep, str):
                continue
            name, spec, resolved = _parse_pep508_entry(dep)
            if not name:
                continue
            records.append(
                DependencyRecord(
                    ecosystem=self.ecosystem,
                    name=name,
                    file_path=relative,
                    current_spec=spec,
                    resolved_version=resolved,
                    latest_version=latest_pypi_version(name),
                    section="project.dependencies",
                )
            )

        opt = project.get("optional-dependencies", {})
        if isinstance(opt, dict):
            for group, deps in opt.items():
                if not isinstance(deps, list):
                    continue
                for dep in deps:
                    if not isinstance(dep, str):
                        continue
                    name, spec, resolved = _parse_pep508_entry(dep)
                    if not name:
                        continue
                    records.append(
                        DependencyRecord(
                            ecosystem=self.ecosystem,
                            name=name,
                            file_path=relative,
                            current_spec=spec,
                            resolved_version=resolved,
                            latest_version=latest_pypi_version(name),
                            section=f"project.optional-dependencies.{group}",
                        )
                    )

        poetry = payload.get("tool", {}).get("poetry", {})
        poetry_deps = poetry.get("dependencies", {})
        if isinstance(poetry_deps, dict):
            records.extend(self._scan_poetry_table(poetry_deps, relative, "tool.poetry.dependencies"))

        poetry_groups = poetry.get("group", {})
        if isinstance(poetry_groups, dict):
            for group_name, group_payload in poetry_groups.items():
                if not isinstance(group_payload, dict):
                    continue
                group_deps = group_payload.get("dependencies", {})
                if not isinstance(group_deps, dict):
                    continue
                records.extend(
                    self._scan_poetry_table(
                        group_deps,
                        relative,
                        f"tool.poetry.group.{group_name}.dependencies",
                    )
                )

        return records

    def _scan_poetry_table(
        self,
        deps: dict,
        relative_path: str,
        section: str,
    ) -> list[DependencyRecord]:
        records: list[DependencyRecord] = []
        for name, spec_value in deps.items():
            if str(name).lower() == "python":
                continue
            spec: str | None = None
            if isinstance(spec_value, str):
                spec = spec_value
            elif isinstance(spec_value, dict) and "version" in spec_value:
                spec = str(spec_value["version"])
            if not spec:
                continue
            resolved = _first_semver(spec)
            records.append(
                DependencyRecord(
                    ecosystem=self.ecosystem,
                    name=str(name),
                    file_path=relative_path,
                    current_spec=spec,
                    resolved_version=resolved,
                    latest_version=latest_pypi_version(str(name)),
                    section=section,
                )
            )
        return records

