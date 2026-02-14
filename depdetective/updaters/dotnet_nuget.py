from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from depdetective.models import DependencyRecord, UpdateAction
from depdetective.updaters.base import BaseUpdater

LITERAL_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?$")


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", maxsplit=1)[1]
    return tag


class DotnetNugetUpdater(BaseUpdater):
    ecosystem = "dotnet"

    def apply_updates(
        self, repo_root: Path, dependencies: list[DependencyRecord], max_updates: int
    ) -> list[UpdateAction]:
        changes: list[UpdateAction] = []
        by_file: dict[str, dict[str, DependencyRecord]] = {}
        for dep in dependencies:
            if dep.ecosystem != self.ecosystem or not dep.update_available:
                continue
            if not dep.latest_version:
                continue
            by_file.setdefault(dep.file_path, {})[dep.name.lower()] = dep

        for relative_file, deps in by_file.items():
            if len(changes) >= max_updates:
                break
            file_path = repo_root / relative_file
            lowered = file_path.name.lower()
            if lowered == "packages.config":
                applied = _update_packages_config(
                    relative_file,
                    file_path,
                    deps,
                    max_updates - len(changes),
                )
            else:
                applied = _update_msbuild_xml(
                    relative_file,
                    file_path,
                    deps,
                    max_updates - len(changes),
                )
            changes.extend(applied)
        return changes


def _update_msbuild_xml(
    relative_file: str,
    file_path: Path,
    deps: dict[str, DependencyRecord],
    max_updates: int,
) -> list[UpdateAction]:
    tree = ET.parse(file_path)
    root = tree.getroot()
    changes: list[UpdateAction] = []
    dirty = False

    for element in root.iter():
        if len(changes) >= max_updates:
            break
        element_name = _local_name(element.tag)
        if element_name not in {"PackageReference", "PackageVersion"}:
            continue
        package_name = element.attrib.get("Include") or element.attrib.get("Update")
        if not package_name:
            continue
        dep = deps.get(package_name.lower())
        if not dep or not dep.latest_version:
            continue

        old_spec = element.attrib.get("Version")
        if old_spec:
            if old_spec == dep.latest_version or "$(" in old_spec or not _is_literal_version(old_spec):
                continue
            element.set("Version", dep.latest_version)
            changes.append(
                UpdateAction(
                    ecosystem="dotnet",
                    file_path=relative_file,
                    dependency=package_name,
                    old_spec=old_spec,
                    new_spec=dep.latest_version,
                    latest_version=dep.latest_version,
                )
            )
            dirty = True
            continue

        for child in element:
            if _local_name(child.tag) != "Version" or not child.text:
                continue
            old_spec = child.text.strip()
            if old_spec == dep.latest_version or "$(" in old_spec or not _is_literal_version(old_spec):
                break
            child.text = dep.latest_version
            changes.append(
                UpdateAction(
                    ecosystem="dotnet",
                    file_path=relative_file,
                    dependency=package_name,
                    old_spec=old_spec,
                    new_spec=dep.latest_version,
                    latest_version=dep.latest_version,
                )
            )
            dirty = True
            break

    if dirty:
        _write_xml(tree, file_path)
    return changes


def _update_packages_config(
    relative_file: str,
    file_path: Path,
    deps: dict[str, DependencyRecord],
    max_updates: int,
) -> list[UpdateAction]:
    tree = ET.parse(file_path)
    root = tree.getroot()
    changes: list[UpdateAction] = []
    dirty = False

    for element in root.iter():
        if len(changes) >= max_updates:
            break
        if _local_name(element.tag) != "package":
            continue
        package_name = element.attrib.get("id")
        old_spec = element.attrib.get("version")
        if not package_name or not old_spec:
            continue
        dep = deps.get(package_name.lower())
        if not dep or not dep.latest_version:
            continue
        if old_spec == dep.latest_version or not _is_literal_version(old_spec):
            continue
        element.set("version", dep.latest_version)
        dirty = True
        changes.append(
            UpdateAction(
                ecosystem="dotnet",
                file_path=relative_file,
                dependency=package_name,
                old_spec=old_spec,
                new_spec=dep.latest_version,
                latest_version=dep.latest_version,
            )
        )

    if dirty:
        _write_xml(tree, file_path)
    return changes


def _write_xml(tree: ET.ElementTree, file_path: Path) -> None:
    content = ET.tostring(tree.getroot(), encoding="unicode")
    if not content.endswith("\n"):
        content += "\n"
    file_path.write_text(content, encoding="utf-8")


def _is_literal_version(value: str) -> bool:
    return bool(LITERAL_VERSION.fullmatch(value.strip()))
