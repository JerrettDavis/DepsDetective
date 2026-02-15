from __future__ import annotations

import re
from pathlib import Path

from depdetective.models import DependencyRecord, UpdateAction
from depdetective.updaters.base import BaseUpdater

REQ_SINGLE = re.compile(r"^(\s*require\s+)(\S+)(\s+)(\S+)(.*)$")
REQ_BLOCK_START = re.compile(r"^\s*require\s*\(\s*$")
REQ_BLOCK_LINE = re.compile(r"^(\s*)(\S+)(\s+)(\S+)(.*)$")
LITERAL_VERSION = re.compile(r"^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def _is_literal_version(value: str) -> bool:
    return bool(LITERAL_VERSION.fullmatch(value.strip()))


class GoModUpdater(BaseUpdater):
    ecosystem = "go"

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
            by_file.setdefault(dep.file_path, {})[dep.name] = dep

        for relative_file, dep_map in by_file.items():
            if len(changes) >= max_updates:
                break
            file_path = repo_root / relative_file
            lines = file_path.read_text(encoding="utf-8").splitlines()
            out: list[str] = []
            in_require_block = False
            dirty = False

            for line in lines:
                if len(changes) >= max_updates:
                    out.append(line)
                    continue

                stripped = line.strip()
                if REQ_BLOCK_START.match(line):
                    in_require_block = True
                    out.append(line)
                    continue
                if in_require_block and stripped == ")":
                    in_require_block = False
                    out.append(line)
                    continue

                if in_require_block:
                    match = REQ_BLOCK_LINE.match(line)
                    if not match:
                        out.append(line)
                        continue
                    prefix, module, spacer, version, suffix = match.groups()
                    dep = dep_map.get(module)
                    if not dep or not dep.latest_version or not _is_literal_version(version):
                        out.append(line)
                        continue
                    if version == dep.latest_version:
                        out.append(line)
                        continue
                    out.append(f"{prefix}{module}{spacer}{dep.latest_version}{suffix}")
                    dirty = True
                    changes.append(
                        UpdateAction(
                            ecosystem=self.ecosystem,
                            file_path=relative_file,
                            dependency=module,
                            old_spec=version,
                            new_spec=dep.latest_version,
                            latest_version=dep.latest_version,
                        )
                    )
                    continue

                match = REQ_SINGLE.match(line)
                if not match:
                    out.append(line)
                    continue
                prefix, module, spacer, version, suffix = match.groups()
                dep = dep_map.get(module)
                if not dep or not dep.latest_version or not _is_literal_version(version):
                    out.append(line)
                    continue
                if version == dep.latest_version:
                    out.append(line)
                    continue
                out.append(f"{prefix}{module}{spacer}{dep.latest_version}{suffix}")
                dirty = True
                changes.append(
                    UpdateAction(
                        ecosystem=self.ecosystem,
                        file_path=relative_file,
                        dependency=module,
                        old_spec=version,
                        new_spec=dep.latest_version,
                        latest_version=dep.latest_version,
                    )
                )

            if dirty:
                file_path.write_text("\n".join(out) + "\n", encoding="utf-8")
        return changes

