from __future__ import annotations

import re
from pathlib import Path

from tomlkit import dumps, parse

from depdetective.models import DependencyRecord, UpdateAction
from depdetective.updaters.base import BaseUpdater

PINNED_REQ = re.compile(
    r"^\s*(?P<name>[A-Za-z0-9_.-]+)(?P<extras>\[[^\]]+\])?\s*==\s*(?P<version>[^\s;,@]+)(?P<rest>.*)$"
)
SEMVER_TOKEN = re.compile(r"(?P<prefix>^[^\d]*)(?P<version>\d+\.\d+\.\d+)(?P<suffix>.*$)")


class PythonPyprojectUpdater(BaseUpdater):
    ecosystem = "python"

    def apply_updates(
        self, repo_root: Path, dependencies: list[DependencyRecord], max_updates: int
    ) -> list[UpdateAction]:
        changes: list[UpdateAction] = []
        by_file: dict[str, list[DependencyRecord]] = {}
        for dep in dependencies:
            if dep.ecosystem != self.ecosystem or not dep.update_available:
                continue
            if not dep.file_path.endswith("pyproject.toml"):
                continue
            if not dep.latest_version:
                continue
            by_file.setdefault(dep.file_path, []).append(dep)

        for relative_file, file_deps in by_file.items():
            if len(changes) >= max_updates:
                break
            file_path = repo_root / relative_file
            doc = parse(file_path.read_text(encoding="utf-8"))
            dirty = False

            for dep in file_deps:
                if len(changes) >= max_updates:
                    break
                new_spec = self._update_dependency(doc, dep)
                if not new_spec:
                    continue
                dirty = True
                changes.append(
                    UpdateAction(
                        ecosystem=self.ecosystem,
                        file_path=relative_file,
                        dependency=dep.name,
                        old_spec=dep.current_spec,
                        new_spec=new_spec,
                        latest_version=dep.latest_version,
                    )
                )

            if dirty:
                file_path.write_text(dumps(doc), encoding="utf-8")

        return changes

    def _update_dependency(self, doc: dict, dep: DependencyRecord) -> str | None:
        section = dep.section or ""
        if section == "project.dependencies":
            return self._update_project_dependencies(doc, dep)
        if section.startswith("project.optional-dependencies."):
            group = section.removeprefix("project.optional-dependencies.")
            return self._update_project_optional_dependencies(doc, group, dep)
        if section == "tool.poetry.dependencies":
            return self._update_poetry_dependencies(doc, dep)
        if section.startswith("tool.poetry.group.") and section.endswith(".dependencies"):
            group = section.removeprefix("tool.poetry.group.").removesuffix(".dependencies")
            return self._update_poetry_group_dependencies(doc, group, dep)
        return None

    def _update_project_dependencies(self, doc: dict, dep: DependencyRecord) -> str | None:
        project = doc.get("project")
        if not project or "dependencies" not in project:
            return None
        return self._update_requirement_array(project["dependencies"], dep)

    def _update_project_optional_dependencies(
        self,
        doc: dict,
        group: str,
        dep: DependencyRecord,
    ) -> str | None:
        project = doc.get("project")
        if not project or "optional-dependencies" not in project:
            return None
        optional = project["optional-dependencies"]
        if group not in optional:
            return None
        return self._update_requirement_array(optional[group], dep)

    def _update_requirement_array(self, requirement_array: list, dep: DependencyRecord) -> str | None:
        for index, requirement in enumerate(requirement_array):
            if not isinstance(requirement, str):
                continue
            matched = PINNED_REQ.match(requirement)
            if not matched:
                continue
            if matched.group("name").lower() != dep.name.lower():
                continue
            new_entry = (
                f"{matched.group('name')}"
                f"{matched.group('extras') or ''}"
                f"=={dep.latest_version}"
                f"{matched.group('rest') or ''}"
            )
            if new_entry == requirement:
                return None
            requirement_array[index] = new_entry
            return f"=={dep.latest_version}"
        return None

    def _update_poetry_dependencies(self, doc: dict, dep: DependencyRecord) -> str | None:
        tool = doc.get("tool")
        if not tool or "poetry" not in tool:
            return None
        poetry = tool["poetry"]
        deps = poetry.get("dependencies")
        if not deps:
            return None
        return self._update_poetry_table(deps, dep)

    def _update_poetry_group_dependencies(
        self,
        doc: dict,
        group: str,
        dep: DependencyRecord,
    ) -> str | None:
        tool = doc.get("tool")
        if not tool or "poetry" not in tool:
            return None
        poetry = tool["poetry"]
        groups = poetry.get("group")
        if not groups or group not in groups:
            return None
        group_deps = groups[group].get("dependencies")
        if not group_deps:
            return None
        return self._update_poetry_table(group_deps, dep)

    def _update_poetry_table(self, table: dict, dep: DependencyRecord) -> str | None:
        key = _lookup_dependency_key(table, dep.name)
        if not key:
            return None

        value = table[key]
        if isinstance(value, str):
            new_value = _replace_semver(value, dep.latest_version)
            if not new_value or new_value == value:
                return None
            table[key] = new_value
            return new_value

        if isinstance(value, dict) and "version" in value and isinstance(value["version"], str):
            old_version = value["version"]
            new_version = _replace_semver(old_version, dep.latest_version)
            if not new_version or new_version == old_version:
                return None
            value["version"] = new_version
            table[key] = value
            return new_version

        return None


def _replace_semver(spec: str, latest: str) -> str | None:
    match = SEMVER_TOKEN.match(spec)
    if not match:
        return None
    return f"{match.group('prefix')}{latest}{match.group('suffix')}"


def _lookup_dependency_key(table: dict, name: str) -> str | None:
    for key in table.keys():
        if str(key).lower() == name.lower():
            return str(key)
    return None

