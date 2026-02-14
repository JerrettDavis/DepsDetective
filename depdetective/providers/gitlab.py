from __future__ import annotations

import os
from urllib.parse import quote

import requests

from depdetective.providers.base import BaseProvider


class GitLabProvider(BaseProvider):
    def __init__(self, repo: str, token_env: str = "GITLAB_TOKEN", host: str = "https://gitlab.com") -> None:
        self.repo = repo
        self.project_id = quote(repo, safe="")
        self.host = host.rstrip("/")
        token = os.getenv(token_env)
        if not token:
            raise ValueError(f"Missing token in env var: {token_env}")
        self.headers = {"PRIVATE-TOKEN": token}

    def open_or_update_pr(
        self,
        source_branch: str,
        target_branch: str,
        title: str,
        body: str,
        labels: list[str],
    ) -> str | None:
        list_url = (
            f"{self.host}/api/v4/projects/{self.project_id}/merge_requests"
            f"?state=opened&source_branch={source_branch}&target_branch={target_branch}"
        )
        response = requests.get(list_url, headers=self.headers, timeout=30)
        response.raise_for_status()
        mrs = response.json()
        label_csv = ",".join(labels)
        if mrs:
            mr = mrs[0]
            iid = mr["iid"]
            patch = requests.put(
                f"{self.host}/api/v4/projects/{self.project_id}/merge_requests/{iid}",
                headers=self.headers,
                data={"title": title, "description": body, "labels": label_csv},
                timeout=30,
            )
            patch.raise_for_status()
            return patch.json().get("web_url")
        create = requests.post(
            f"{self.host}/api/v4/projects/{self.project_id}/merge_requests",
            headers=self.headers,
            data={
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
                "description": body,
                "labels": label_csv,
            },
            timeout=30,
        )
        create.raise_for_status()
        return create.json().get("web_url")

