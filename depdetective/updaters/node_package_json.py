from __future__ import annotations

import json
from pathlib import Path

from depdetective.models import DependencyRecord, UpdateAction
from depdetective.updaters.base import BaseUpdater


def _prefix(spec: str) -> str:
    if spec.startswith("^"):
        return "^"
    if spec.startswith("~"):
        return "~"
    return ""


class NodePackageUpdater(BaseUpdater):
    ecosystem = "node"

    def apply_updates(
        self, repo_root: Path, dependencies: list[DependencyRecord], max_updates: int
    ) -> list[UpdateAction]:
        changes: list[UpdateAction] = []
        by_file: dict[str, list[DependencyRecord]] = {}
        for dep in dependencies:
            if dep.ecosystem != self.ecosystem or not dep.update_available:
                continue
            if not dep.latest_version:
                continue
            by_file.setdefault(dep.file_path, []).append(dep)

        for relative_file, deps in by_file.items():
            if len(changes) >= max_updates:
                break
            file_path = repo_root / relative_file
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            dirty = False
            for dep in deps:
                if len(changes) >= max_updates:
                    break
                section = dep.section or "dependencies"
                section_obj = payload.get(section, {})
                if dep.name not in section_obj:
                    continue
                old_spec = str(section_obj[dep.name])
                new_spec = f"{_prefix(old_spec)}{dep.latest_version}"
                if old_spec == new_spec:
                    continue
                section_obj[dep.name] = new_spec
                payload[section] = section_obj
                dirty = True
                changes.append(
                    UpdateAction(
                        ecosystem=self.ecosystem,
                        file_path=relative_file,
                        dependency=dep.name,
                        old_spec=old_spec,
                        new_spec=new_spec,
                        latest_version=dep.latest_version,
                    )
                )
            if dirty:
                file_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return changes

