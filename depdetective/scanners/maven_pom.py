from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.registry_clients import latest_maven_version
from depdetective.scanners.base import BaseScanner

LITERAL_VERSION = re.compile(r"^\d+(?:\.\d+)*(?:[-+][0-9A-Za-z.-]+)?$")


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", maxsplit=1)[1]
    return tag


def _child_text(element: ET.Element, child_name: str) -> str | None:
    for child in element:
        if _local_name(child.tag) == child_name and child.text:
            return child.text.strip()
    return None


def _extract_resolved_version(version: str) -> str | None:
    trimmed = version.strip()
    if "${" in trimmed:
        return None
    if not LITERAL_VERSION.fullmatch(trimmed):
        return None
    return trimmed


class MavenPomScanner(BaseScanner):
    ecosystem = "maven"

    def discover_files(self, repo_root: Path) -> list[Path]:
        return [
            path
            for path in repo_root.rglob("pom.xml")
            if ".git" not in path.parts and "target" not in path.parts
        ]

    def scan_file(self, file_path: Path, repo_root: Path) -> list[DependencyRecord]:
        relative = str(file_path.relative_to(repo_root))
        try:
            root = ET.fromstring(file_path.read_text(encoding="utf-8"))
        except ET.ParseError:
            return []

        records: list[DependencyRecord] = []
        for element in root.iter():
            if _local_name(element.tag) != "dependency":
                continue
            group_id = _child_text(element, "groupId")
            artifact_id = _child_text(element, "artifactId")
            version = _child_text(element, "version")
            if not group_id or not artifact_id or not version:
                continue
            package_name = f"{group_id}:{artifact_id}"
            records.append(
                DependencyRecord(
                    ecosystem=self.ecosystem,
                    name=package_name,
                    file_path=relative,
                    current_spec=version,
                    resolved_version=_extract_resolved_version(version),
                    latest_version=latest_maven_version(group_id, artifact_id),
                    section="dependency",
                )
            )
        return records

