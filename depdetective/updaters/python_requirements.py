from __future__ import annotations

import re
from pathlib import Path

from depdetective.models import DependencyRecord, UpdateAction
from depdetective.updaters.base import BaseUpdater

REQ_LINE = re.compile(r"^(\s*)([A-Za-z0-9_.-]+)(\s*)(==)(\s*)([^\s;]+)(.*)$")


class PythonRequirementsUpdater(BaseUpdater):
    ecosystem = "python"

    def apply_updates(
        self, repo_root: Path, dependencies: list[DependencyRecord], max_updates: int
    ) -> list[UpdateAction]:
        changes: list[UpdateAction] = []
        by_file: dict[str, dict[str, DependencyRecord]] = {}
        for dep in dependencies:
            if dep.ecosystem != self.ecosystem or not dep.update_available:
                continue
            if not dep.latest_version or not dep.resolved_version:
                continue
            by_file.setdefault(dep.file_path, {})[dep.name.lower()] = dep

        for relative_file, dep_map in by_file.items():
            file_path = repo_root / relative_file
            lines = file_path.read_text(encoding="utf-8").splitlines()
            updated_lines: list[str] = []
            dirty = False
            for line in lines:
                if len(changes) >= max_updates:
                    updated_lines.append(line)
                    continue
                match = REQ_LINE.match(line)
                if not match:
                    updated_lines.append(line)
                    continue
                prefix_ws, name, ws_name, op, ws_op, version, suffix = match.groups()
                dep = dep_map.get(name.lower())
                if not dep or not dep.latest_version or version == dep.latest_version:
                    updated_lines.append(line)
                    continue
                new_line = f"{prefix_ws}{name}{ws_name}{op}{ws_op}{dep.latest_version}{suffix}"
                updated_lines.append(new_line)
                dirty = True
                changes.append(
                    UpdateAction(
                        ecosystem=self.ecosystem,
                        file_path=relative_file,
                        dependency=name,
                        old_spec=f"=={version}",
                        new_spec=f"=={dep.latest_version}",
                        latest_version=dep.latest_version,
                    )
                )
            if dirty:
                file_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")
        return changes
