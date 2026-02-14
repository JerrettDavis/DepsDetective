from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from depdetective.models import DependencyRecord


class BaseScanner(ABC):
    ecosystem: str

    @abstractmethod
    def discover_files(self, repo_root: Path) -> list[Path]:
        raise NotImplementedError

    @abstractmethod
    def scan_file(self, file_path: Path, repo_root: Path) -> list[DependencyRecord]:
        raise NotImplementedError

