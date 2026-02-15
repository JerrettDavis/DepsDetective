from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from depdetective.models import DependencyRecord, UpdateAction
from depdetective.updaters.base import BaseUpdater

LITERAL_VERSION = re.compile(r"^\d+(?:\.\d+)*(?:[-+][0-9A-Za-z.-]+)?$")


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", maxsplit=1)[1]
    return tag


def _child(element: ET.Element, child_name: str) -> ET.Element | None:
    for child in element:
        if _local_name(child.tag) == child_name:
            return child
    return None


def _is_literal_version(value: str) -> bool:
    trimmed = value.strip()
    return "${" not in trimmed and bool(LITERAL_VERSION.fullmatch(trimmed))


class MavenPomUpdater(BaseUpdater):
    ecosystem = "maven"

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
            if len(changes) >= max_updates:
                break
            file_path = repo_root / relative_file
            try:
                tree = ET.parse(file_path)
            except ET.ParseError:
                continue
            root = tree.getroot()
            dirty = False

            for dependency in root.iter():
                if len(changes) >= max_updates:
                    break
                if _local_name(dependency.tag) != "dependency":
                    continue
                group_id_element = _child(dependency, "groupId")
                artifact_id_element = _child(dependency, "artifactId")
                version_element = _child(dependency, "version")
                if group_id_element is None or not group_id_element.text:
                    continue
                if artifact_id_element is None or not artifact_id_element.text:
                    continue
                if version_element is None or not version_element.text:
                    continue
                package_name = f"{group_id_element.text.strip()}:{artifact_id_element.text.strip()}"
                dep = dep_map.get(package_name.lower())
                if not dep or not dep.latest_version:
                    continue
                old_spec = version_element.text.strip()
                if old_spec == dep.latest_version or not _is_literal_version(old_spec):
                    continue
                version_element.text = dep.latest_version
                changes.append(
                    UpdateAction(
                        ecosystem=self.ecosystem,
                        file_path=relative_file,
                        dependency=package_name,
                        old_spec=old_spec,
                        new_spec=dep.latest_version,
                        latest_version=dep.latest_version,
                    )
                )
                dirty = True

            if dirty:
                content = ET.tostring(root, encoding="unicode")
                if not content.endswith("\n"):
                    content += "\n"
                file_path.write_text(content, encoding="utf-8")
        return changes
