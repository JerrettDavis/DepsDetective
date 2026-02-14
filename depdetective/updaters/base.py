from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from depdetective.models import DependencyRecord, UpdateAction


class BaseUpdater(ABC):
    ecosystem: str

    @abstractmethod
    def apply_updates(
        self, repo_root: Path, dependencies: list[DependencyRecord], max_updates: int
    ) -> list[UpdateAction]:
        raise NotImplementedError

