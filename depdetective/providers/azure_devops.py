from __future__ import annotations

import base64
import os
from urllib.parse import quote

import requests

from depdetective.providers.base import BaseProvider


class AzureDevOpsProvider(BaseProvider):
    def __init__(
        self,
        repo: str,
        token_env: str = "AZURE_DEVOPS_TOKEN",
        host: str = "https://dev.azure.com",
    ) -> None:
        self.repo = repo
        self.host = host.rstrip("/")
        organization, project, repository = _parse_repo(repo)
        self.organization = organization
        self.project = project
        self.repository = repository
        self.encoded_repository = quote(repository, safe="")
        token = os.getenv(token_env)
        auth_env = token_env
        if not token:
            token = os.getenv("SYSTEM_ACCESSTOKEN")
            if token:
                auth_env = "SYSTEM_ACCESSTOKEN"
        if not token:
            raise ValueError(f"Missing token in env var: {token_env}")
        self.headers = {
            "Content-Type": "application/json",
            **_build_auth_header(token, auth_env),
        }

    def open_or_update_pr(
        self,
        source_branch: str,
        target_branch: str,
        title: str,
        body: str,
        labels: list[str],
    ) -> str | None:
        source_ref = _as_ref(source_branch)
        target_ref = _as_ref(target_branch)
        pulls = self._find_open_pull_requests(source_ref, target_ref)
        description = _append_labels_to_description(body, labels)

        if pulls:
            pr = pulls[0]
            pr_id = pr["pullRequestId"]
            patch = requests.patch(
                self._pr_url(pr_id),
                headers=self.headers,
                json={"title": title, "description": description},
                timeout=30,
            )
            patch.raise_for_status()
            payload = patch.json()
            return _extract_web_url(payload) or _build_pr_fallback_url(
                self.host,
                self.organization,
                self.project,
                self.repository,
                pr_id,
            )

        create = requests.post(
            self._pull_requests_url(),
            headers=self.headers,
            json={
                "sourceRefName": source_ref,
                "targetRefName": target_ref,
                "title": title,
                "description": description,
            },
            timeout=30,
        )
        create.raise_for_status()
        payload = create.json()
        pr_id = payload.get("pullRequestId")
        if pr_id is None:
            return _extract_web_url(payload)
        return _extract_web_url(payload) or _build_pr_fallback_url(
            self.host,
            self.organization,
            self.project,
            self.repository,
            int(pr_id),
        )

    def _find_open_pull_requests(self, source_ref: str, target_ref: str) -> list[dict]:
        response = requests.get(
            self._pull_requests_url(),
            headers=self.headers,
            params={
                "searchCriteria.status": "active",
                "searchCriteria.sourceRefName": source_ref,
                "searchCriteria.targetRefName": target_ref,
                "api-version": "7.1",
            },
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        return payload.get("value", [])

    def _pull_requests_url(self) -> str:
        return (
            f"{self.host}/{self.organization}/{self.project}/_apis/git/repositories/"
            f"{self.encoded_repository}/pullrequests?api-version=7.1"
        )

    def _pr_url(self, pr_id: int) -> str:
        return (
            f"{self.host}/{self.organization}/{self.project}/_apis/git/repositories/"
            f"{self.encoded_repository}/pullrequests/{pr_id}?api-version=7.1"
        )


def _parse_repo(repo: str) -> tuple[str, str, str]:
    parts = [part for part in repo.split("/") if part]
    if len(parts) != 3:
        raise ValueError("Azure DevOps provider repo must be '<org>/<project>/<repo>'")
    return parts[0], parts[1], parts[2]


def _build_auth_header(token: str, token_env: str) -> dict[str, str]:
    if token_env.upper().startswith("SYSTEM_"):
        return {"Authorization": f"Bearer {token}"}
    basic = base64.b64encode(f":{token}".encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {basic}"}


def _extract_web_url(payload: dict) -> str | None:
    links = payload.get("_links", {})
    web = links.get("web", {})
    href = web.get("href")
    if isinstance(href, str) and href:
        return href
    url = payload.get("url")
    if isinstance(url, str) and "/_apis/" in url:
        return url.replace("/_apis/git/repositories", "/_git").replace("/pullrequests", "/pullrequest")
    return None


def _build_pr_fallback_url(
    host: str,
    organization: str,
    project: str,
    repository: str,
    pr_id: int,
) -> str:
    encoded_repo = quote(repository, safe="")
    return f"{host}/{organization}/{project}/_git/{encoded_repo}/pullrequest/{pr_id}"


def _as_ref(branch: str) -> str:
    if branch.startswith("refs/heads/"):
        return branch
    return f"refs/heads/{branch}"


def _append_labels_to_description(description: str, labels: list[str]) -> str:
    if not labels:
        return description
    suffix = f"\n\nLabels: {', '.join(labels)}"
    if suffix.strip() in description:
        return description
    return f"{description}{suffix}"
