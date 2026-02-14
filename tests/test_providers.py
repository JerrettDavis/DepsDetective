import base64

from depdetective.providers import build_provider, infer_repo_slug
from depdetective.providers.azure_devops import AzureDevOpsProvider


def test_infer_repo_slug_https() -> None:
    assert infer_repo_slug("https://github.com/org/repo.git", provider_type="github") == "org/repo"


def test_infer_repo_slug_ssh() -> None:
    assert infer_repo_slug("git@github.com:org/repo.git", provider_type="github") == "org/repo"


def test_infer_repo_slug_gitlab_subgroup() -> None:
    assert (
        infer_repo_slug("https://gitlab.com/group/subgroup/repo.git", provider_type="gitlab")
        == "group/subgroup/repo"
    )


def test_infer_repo_slug_azure_devops() -> None:
    assert (
        infer_repo_slug(
            "https://dev.azure.com/org/project/_git/repo",
            provider_type="azure_devops",
        )
        == "org/project/repo"
    )


def test_build_provider_azure_alias(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_TOKEN", "token-1")
    provider = build_provider(
        provider_type="ado",
        repo="org/project/repo",
        token_env=None,
        host=None,
    )
    assert isinstance(provider, AzureDevOpsProvider)


def test_azure_provider_uses_basic_auth_header(monkeypatch) -> None:
    token = "abc123"
    monkeypatch.setenv("AZURE_DEVOPS_TOKEN", token)
    provider = AzureDevOpsProvider(repo="org/project/repo")
    expected = base64.b64encode(f":{token}".encode("utf-8")).decode("utf-8")
    assert provider.headers["Authorization"] == f"Basic {expected}"


def test_azure_provider_uses_bearer_for_system_access_token(monkeypatch) -> None:
    monkeypatch.delenv("AZURE_DEVOPS_TOKEN", raising=False)
    monkeypatch.setenv("SYSTEM_ACCESSTOKEN", "system-token")
    provider = AzureDevOpsProvider(repo="org/project/repo")
    assert provider.headers["Authorization"] == "Bearer system-token"
