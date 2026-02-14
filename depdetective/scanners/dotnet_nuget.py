from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.registry_clients import latest_nuget_version
from depdetective.scanners.base import BaseScanner

LITERAL_VERSION = re.compile(r"^\d+\.\d+\.\d+(?:\.\d+)?(?:[-+][0-9A-Za-z.-]+)?$")
PROJECT_SUFFIXES = {".csproj", ".fsproj", ".vbproj", ".props", ".targets"}


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.rsplit("}", maxsplit=1)[1]
    return tag


def _extract_resolved_version(spec: str) -> str | None:
    if "$(" in spec:
        return None
    trimmed = spec.strip()
    if not LITERAL_VERSION.fullmatch(trimmed):
        return None
    return trimmed


class DotnetNugetScanner(BaseScanner):
    ecosystem = "dotnet"

    def discover_files(self, repo_root: Path) -> list[Path]:
        files: list[Path] = []
        for path in repo_root.rglob("*"):
            if not path.is_file():
                continue
            if ".git" in path.parts or "bin" in path.parts or "obj" in path.parts:
                continue
            if path.suffix.lower() in PROJECT_SUFFIXES:
                files.append(path)
                continue
            lowered = path.name.lower()
            if lowered in {"directory.packages.props", "packages.config"}:
                files.append(path)
        return files

    def scan_file(self, file_path: Path, repo_root: Path) -> list[DependencyRecord]:
        lowered = file_path.name.lower()
        if lowered == "packages.config":
            return self._scan_packages_config(file_path, repo_root)
        return self._scan_msbuild_xml(file_path, repo_root)

    def _scan_msbuild_xml(self, file_path: Path, repo_root: Path) -> list[DependencyRecord]:
        root = ET.fromstring(file_path.read_text(encoding="utf-8"))
        relative = str(file_path.relative_to(repo_root))
        records: list[DependencyRecord] = []
        for element in root.iter():
            element_name = _local_name(element.tag)
            if element_name not in {"PackageReference", "PackageVersion"}:
                continue
            package_name = element.attrib.get("Include") or element.attrib.get("Update")
            if not package_name:
                continue
            spec = element.attrib.get("Version")
            if not spec:
                for child in element:
                    if _local_name(child.tag) == "Version" and child.text:
                        spec = child.text.strip()
                        break
            if not spec:
                continue
            resolved = _extract_resolved_version(spec)
            records.append(
                DependencyRecord(
                    ecosystem=self.ecosystem,
                    name=package_name,
                    file_path=relative,
                    current_spec=spec,
                    resolved_version=resolved,
                    latest_version=latest_nuget_version(package_name),
                    section=element_name,
                )
            )
        return records

    def _scan_packages_config(self, file_path: Path, repo_root: Path) -> list[DependencyRecord]:
        root = ET.fromstring(file_path.read_text(encoding="utf-8"))
        relative = str(file_path.relative_to(repo_root))
        records: list[DependencyRecord] = []
        for element in root.iter():
            if _local_name(element.tag) != "package":
                continue
            package_name = element.attrib.get("id")
            spec = element.attrib.get("version")
            if not package_name or not spec:
                continue
            records.append(
                DependencyRecord(
                    ecosystem=self.ecosystem,
                    name=package_name,
                    file_path=relative,
                    current_spec=spec,
                    resolved_version=_extract_resolved_version(spec),
                    latest_version=latest_nuget_version(package_name),
                    section="packages.config",
                )
            )
        return records
