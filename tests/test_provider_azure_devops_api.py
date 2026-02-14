from __future__ import annotations

from dataclasses import dataclass

from depdetective.providers.azure_devops import AzureDevOpsProvider


@dataclass
class _FakeResponse:
    payload: dict
    status_code: int = 200

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")

    def json(self) -> dict:
        return self.payload


def test_ado_provider_updates_existing_pr(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_TOKEN", "token")
    captured: dict = {}

    def fake_get(url: str, headers: dict, params: dict, timeout: int) -> _FakeResponse:
        captured["get_url"] = url
        captured["params"] = params
        return _FakeResponse({"value": [{"pullRequestId": 42}]})

    def fake_patch(url: str, headers: dict, json: dict, timeout: int) -> _FakeResponse:
        captured["patch_url"] = url
        captured["patch_payload"] = json
        return _FakeResponse({"pullRequestId": 42, "_links": {"web": {"href": "https://ado/pr/42"}}})

    monkeypatch.setattr("depdetective.providers.azure_devops.requests.get", fake_get)
    monkeypatch.setattr("depdetective.providers.azure_devops.requests.patch", fake_patch)

    provider = AzureDevOpsProvider(repo="org/project/repo")
    pr_url = provider.open_or_update_pr(
        source_branch="depdetective/autoupdate",
        target_branch="main",
        title="deps",
        body="body",
        labels=["dependencies"],
    )

    assert "searchCriteria.status" in captured["params"]
    assert captured["patch_payload"]["title"] == "deps"
    assert "Labels: dependencies" in captured["patch_payload"]["description"]
    assert pr_url == "https://ado/pr/42"


def test_ado_provider_creates_new_pr(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_DEVOPS_TOKEN", "token")
    captured: dict = {}

    def fake_get(url: str, headers: dict, params: dict, timeout: int) -> _FakeResponse:
        return _FakeResponse({"value": []})

    def fake_post(url: str, headers: dict, json: dict, timeout: int) -> _FakeResponse:
        captured["post_url"] = url
        captured["post_payload"] = json
        return _FakeResponse({"pullRequestId": 7, "_links": {"web": {"href": "https://ado/pr/7"}}})

    monkeypatch.setattr("depdetective.providers.azure_devops.requests.get", fake_get)
    monkeypatch.setattr("depdetective.providers.azure_devops.requests.post", fake_post)

    provider = AzureDevOpsProvider(repo="org/project/repo")
    pr_url = provider.open_or_update_pr(
        source_branch="depdetective/autoupdate",
        target_branch="main",
        title="deps",
        body="body",
        labels=[],
    )

    assert captured["post_payload"]["sourceRefName"] == "refs/heads/depdetective/autoupdate"
    assert captured["post_payload"]["targetRefName"] == "refs/heads/main"
    assert pr_url == "https://ado/pr/7"

