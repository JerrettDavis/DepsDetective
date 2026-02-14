from depdetective.config import DepDetectiveConfig, ProviderConfig, RepoConfig
from depdetective.runner import _build_clone_url


def test_build_clone_url_github_injects_token(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "abc123")
    config = DepDetectiveConfig(
        repo=RepoConfig(url="https://github.com/org/repo.git"),
        provider=ProviderConfig(type="github"),
    )
    clone_url = _build_clone_url(config)
    assert clone_url.startswith("https://x-access-token:abc123@github.com/")


def test_build_clone_url_azure_injects_token(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_TOKEN", "secret")
    config = DepDetectiveConfig(
        repo=RepoConfig(url="https://dev.azure.com/org/proj/_git/repo"),
        provider=ProviderConfig(type="azure_devops"),
    )
    clone_url = _build_clone_url(config)
    assert clone_url.startswith("https://build:secret@dev.azure.com/")

