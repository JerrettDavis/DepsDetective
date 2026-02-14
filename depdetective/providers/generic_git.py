from __future__ import annotations

from depdetective.providers.base import BaseProvider


class GenericGitProvider(BaseProvider):
    def open_or_update_pr(
        self,
        source_branch: str,
        target_branch: str,
        title: str,
        body: str,
        labels: list[str],
    ) -> str | None:
        return None

