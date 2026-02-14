from __future__ import annotations

import os

import requests

from depdetective.providers.base import BaseProvider


class GitHubProvider(BaseProvider):
    def __init__(
        self,
        repo: str,
        token_env: str = "GITHUB_TOKEN",
        host: str = "https://api.github.com",
    ) -> None:
        self.repo = repo
        self.host = host.rstrip("/")
        token = os.getenv(token_env)
        if not token:
            raise ValueError(f"Missing token in env var: {token_env}")
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        }

    def open_or_update_pr(
        self,
        source_branch: str,
        target_branch: str,
        title: str,
        body: str,
        labels: list[str],
    ) -> str | None:
        owner = self.repo.split("/")[0]
        list_url = (
            f"{self.host}/repos/{self.repo}/pulls"
            f"?state=open&head={owner}:{source_branch}&base={target_branch}"
        )
        response = requests.get(list_url, headers=self.headers, timeout=30)
        response.raise_for_status()
        pulls = response.json()
        if pulls:
            pr = pulls[0]
            pr_number = pr["number"]
            patch = requests.patch(
                f"{self.host}/repos/{self.repo}/pulls/{pr_number}",
                headers=self.headers,
                json={"title": title, "body": body},
                timeout=30,
            )
            patch.raise_for_status()
            self._set_labels(pr_number, labels)
            return patch.json().get("html_url")

        create = requests.post(
            f"{self.host}/repos/{self.repo}/pulls",
            headers=self.headers,
            json={
                "title": title,
                "head": source_branch,
                "base": target_branch,
                "body": body,
            },
            timeout=30,
        )
        create.raise_for_status()
        created = create.json()
        pr_number = created["number"]
        self._set_labels(pr_number, labels)
        return created.get("html_url")

    def _set_labels(self, pr_number: int, labels: list[str]) -> None:
        if not labels:
            return
        label_response = requests.post(
            f"{self.host}/repos/{self.repo}/issues/{pr_number}/labels",
            headers=self.headers,
            json={"labels": labels},
            timeout=30,
        )
        label_response.raise_for_status()
