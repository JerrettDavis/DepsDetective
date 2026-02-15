from __future__ import annotations

import re
from collections.abc import MutableMapping
from pathlib import Path

from tomlkit import dumps, parse

from depdetective.models import DependencyRecord, UpdateAction
from depdetective.updaters.base import BaseUpdater

SEMVER_TOKEN = re.compile(r"(?P<prefix>^[^\d]*)(?P<version>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)(?P<suffix>.*$)")
DEPENDENCY_KEYS = ("dependencies", "dev-dependencies", "build-dependencies")


def _replace_semver(spec: str, latest: str) -> str | None:
    match = SEMVER_TOKEN.match(spec)
    if not match:
        return None
    return f"{match.group('prefix')}{latest}{match.group('suffix')}"


def _iter_dependency_tables(doc: MutableMapping) -> list[tuple[str, MutableMapping]]:
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


class RustCargoUpdater(BaseUpdater):
    ecosystem = "rust"

    def apply_updates(
        self, repo_root: Path, dependencies: list[DependencyRecord], max_updates: int
    ) -> list[UpdateAction]:
        changes: list[UpdateAction] = []
        by_file: dict[str, dict[tuple[str, str], DependencyRecord]] = {}

        for dep in dependencies:
            if dep.ecosystem != self.ecosystem or not dep.update_available:
                continue
            if not dep.latest_version or not dep.section:
                continue
            by_file.setdefault(dep.file_path, {})[(dep.section, dep.name.lower())] = dep

        for relative_file, dep_map in by_file.items():
            if len(changes) >= max_updates:
                break
            file_path = repo_root / relative_file
            doc = parse(file_path.read_text(encoding="utf-8"))
            dirty = False

            for section, table in _iter_dependency_tables(doc):
                for dep_name, dep_spec in list(table.items()):
                    if len(changes) >= max_updates:
                        break
                    dep = dep_map.get((section, str(dep_name).lower()))
                    if not dep or not dep.latest_version:
                        continue

                    if isinstance(dep_spec, str):
                        old_spec = dep_spec
                        new_spec = _replace_semver(old_spec, dep.latest_version)
                        if not new_spec or new_spec == old_spec:
                            continue
                        table[dep_name] = new_spec
                    elif isinstance(dep_spec, MutableMapping) and "version" in dep_spec:
                        old_spec = str(dep_spec["version"])
                        new_spec = _replace_semver(old_spec, dep.latest_version)
                        if not new_spec or new_spec == old_spec:
                            continue
                        dep_spec["version"] = new_spec
                        table[dep_name] = dep_spec
                    else:
                        continue

                    dirty = True
                    changes.append(
                        UpdateAction(
                            ecosystem=self.ecosystem,
                            file_path=relative_file,
                            dependency=str(dep_name),
                            old_spec=old_spec,
                            new_spec=new_spec,
                            latest_version=dep.latest_version,
                        )
                    )

            if dirty:
                file_path.write_text(dumps(doc), encoding="utf-8")

        return changes

