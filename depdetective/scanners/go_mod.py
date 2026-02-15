from __future__ import annotations

import re
from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.registry_clients import latest_go_version
from depdetective.scanners.base import BaseScanner

REQ_SINGLE = re.compile(r"^\s*require\s+(\S+)\s+(\S+)")
REQ_BLOCK_START = re.compile(r"^\s*require\s*\(\s*$")
REQ_BLOCK_LINE = re.compile(r"^\s*(\S+)\s+(\S+)")
LITERAL_VERSION = re.compile(r"^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")


def _extract_resolved_version(spec: str) -> str | None:
    trimmed = spec.strip()
    if LITERAL_VERSION.fullmatch(trimmed):
        return trimmed
    return None


class GoModScanner(BaseScanner):
    ecosystem = "go"

    def discover_files(self, repo_root: Path) -> list[Path]:
        return [
            path
            for path in repo_root.rglob("go.mod")
            if ".git" not in path.parts and "vendor" not in path.parts
        ]

    def scan_file(self, file_path: Path, repo_root: Path) -> list[DependencyRecord]:
        relative = str(file_path.relative_to(repo_root))
        records: list[DependencyRecord] = []
        in_require_block = False

        for line in file_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("//"):
                continue

            if REQ_BLOCK_START.match(line):
                in_require_block = True
                continue
            if in_require_block and stripped == ")":
                in_require_block = False
                continue

            module: str | None = None
            version: str | None = None
            if in_require_block:
                block_match = REQ_BLOCK_LINE.match(line)
                if block_match:
                    module = block_match.group(1)
                    version = block_match.group(2)
            else:
                single_match = REQ_SINGLE.match(line)
                if single_match:
                    module = single_match.group(1)
                    version = single_match.group(2)

            if not module or not version:
                continue

            resolved = _extract_resolved_version(version)
            records.append(
                DependencyRecord(
                    ecosystem=self.ecosystem,
                    name=module,
                    file_path=relative,
                    current_spec=version,
                    resolved_version=resolved,
                    latest_version=latest_go_version(module),
                    section="require",
                )
            )
        return records

