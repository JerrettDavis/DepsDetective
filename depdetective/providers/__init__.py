from __future__ import annotations

import re

from depdetective.providers.azure_devops import AzureDevOpsProvider
from depdetective.providers.base import BaseProvider
from depdetective.providers.generic_git import GenericGitProvider
from depdetective.providers.github import GitHubProvider
from depdetective.providers.gitlab import GitLabProvider


def build_provider(
    provider_type: str,
    repo: str | None,
    token_env: str | None,
    host: str | None = None,
    repo_url: str | None = None,
) -> BaseProvider:
    kind = provider_type.lower()
    repo_slug = repo or infer_repo_slug(repo_url or "", provider_type=kind)
    if kind == "github":
        if not repo_slug:
            raise ValueError("provider.repo is required for GitHub provider")
        return GitHubProvider(
            repo=repo_slug,
            token_env=token_env or "GITHUB_TOKEN",
            host=host or "https://api.github.com",
        )
    if kind == "gitlab":
        if not repo_slug:
            raise ValueError("provider.repo is required for GitLab provider")
        return GitLabProvider(
            repo=repo_slug,
            token_env=token_env or "GITLAB_TOKEN",
            host=host or "https://gitlab.com",
        )
    if kind in {"azure_devops", "ado", "azure"}:
        if not repo_slug:
            raise ValueError("provider.repo is required for Azure DevOps provider")
        return AzureDevOpsProvider(
            repo=repo_slug,
            token_env=token_env or "AZURE_DEVOPS_TOKEN",
            host=host or "https://dev.azure.com",
        )
    return GenericGitProvider()


def infer_repo_slug(repo_url: str, provider_type: str | None = None) -> str | None:
    if not repo_url:
        return None
    kind = (provider_type or "").lower()

    if kind in {"azure_devops", "ado", "azure"}:
        return _infer_azure_devops_repo_slug(repo_url)

    candidates = [  # path capture keeps nested groups for GitLab
        r"^https?://[^/]+/(.+?)(?:\.git)?/?$",
        r"^git@[^:]+:(.+?)(?:\.git)?$",
        r"^ssh://git@[^/]+/(.+?)(?:\.git)?/?$",
    ]
    for pattern in candidates:
        match = re.match(pattern, repo_url)
        if match:
            path = match.group(1).strip("/")
            if not path:
                return None
            if kind == "github":
                parts = path.split("/")
                if len(parts) >= 2:
                    return "/".join(parts[:2])
                return None
            return path
    return None


def _infer_azure_devops_repo_slug(repo_url: str) -> str | None:
    # https://dev.azure.com/{org}/{project}/_git/{repo}
    dev_match = re.match(
        r"^https?://[^/]+/([^/]+)/([^/]+)/_git/([^/]+?)(?:\.git)?/?$",
        repo_url,
    )
    if dev_match:
        return "/".join(dev_match.groups())

    # ssh://git@ssh.dev.azure.com:v3/{org}/{project}/{repo}
    ssh_match = re.match(
        r"^ssh://git@[^:]+:v3/([^/]+)/([^/]+)/([^/]+?)(?:\.git)?/?$",
        repo_url,
    )
    if ssh_match:
        return "/".join(ssh_match.groups())

    return None
