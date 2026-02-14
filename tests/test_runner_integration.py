from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

from depdetective.config import (
    AutomationConfig,
    DepDetectiveConfig,
    HookConfig,
    ProviderConfig,
    RepoConfig,
    ScanConfig,
    UpdateConfig,
)
from depdetective.runner import run_bot


def _run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr}")
    return result.stdout


def _init_bare_remote(tmp_path: Path) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"
    work = tmp_path / "work"
    _run(["git", "init", "--bare", str(remote)])
    _run(["git", "init", str(work)])
    _run(["git", "checkout", "-b", "main"], cwd=work)
    _run(["git", "config", "user.name", "test-bot"], cwd=work)
    _run(["git", "config", "user.email", "test-bot@example.com"], cwd=work)
    return remote, work


def _push_main(work: Path, remote: Path) -> None:
    _run(["git", "add", "."], cwd=work)
    _run(["git", "commit", "-m", "initial"], cwd=work)
    _run(["git", "remote", "add", "origin", str(remote)], cwd=work)
    _run(["git", "push", "-u", "origin", "main"], cwd=work)


def _remote_branch_exists(remote: Path, branch: str) -> bool:
    output = _run(["git", "ls-remote", "--heads", str(remote), branch])
    return bool(output.strip())


def _remote_show_file(remote: Path, branch: str, file_path: str) -> str:
    return _run(["git", f"--git-dir={remote}", "show", f"refs/heads/{branch}:{file_path}"])


@dataclass
class _FakeProvider:
    called: bool = False
    source_branch: str | None = None
    target_branch: str | None = None

    def open_or_update_pr(
        self,
        source_branch: str,
        target_branch: str,
        title: str,
        body: str,
        labels: list[str],
    ) -> str:
        self.called = True
        self.source_branch = source_branch
        self.target_branch = target_branch
        return "https://example.invalid/pr/1"


def test_run_bot_triggers_provider_workflow_without_real_pr(
    tmp_path: Path,
    monkeypatch,
) -> None:
    remote, work = _init_bare_remote(tmp_path)
    (work / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    _push_main(work, remote)

    fake_provider = _FakeProvider()
    monkeypatch.setattr(
        "depdetective.scanners.python_requirements.latest_pypi_version",
        lambda _name: "2.32.3",
    )
    monkeypatch.setattr("depdetective.runner.build_provider", lambda *args, **kwargs: fake_provider)

    config = DepDetectiveConfig(
        repo=RepoConfig(url=str(remote), base_branch="main"),
        provider=ProviderConfig(type="github", repo="example/repo"),
        scan=ScanConfig(ecosystems=[], auto_detect=True, include_vulnerabilities=False),
        update=UpdateConfig(enabled=True, max_updates=10),
        automation=AutomationConfig(branch_name="depdetective/autoupdate"),
        hooks=HookConfig(),
    )
    report = run_bot(config)

    assert len(report.updates_applied) == 1
    assert report.provider_pr_url == "https://example.invalid/pr/1"
    assert fake_provider.called is True
    assert fake_provider.source_branch == "depdetective/autoupdate"
    assert fake_provider.target_branch == "main"
    assert _remote_branch_exists(remote, "depdetective/autoupdate")
    updated = _remote_show_file(remote, "depdetective/autoupdate", "requirements.txt")
    assert "requests==2.32.3" in updated


def test_run_bot_no_updates_does_not_trigger_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    remote, work = _init_bare_remote(tmp_path)
    (work / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    _push_main(work, remote)

    fake_provider = _FakeProvider()
    monkeypatch.setattr(
        "depdetective.scanners.python_requirements.latest_pypi_version",
        lambda _name: "2.31.0",
    )
    monkeypatch.setattr("depdetective.runner.build_provider", lambda *args, **kwargs: fake_provider)

    config = DepDetectiveConfig(
        repo=RepoConfig(url=str(remote), base_branch="main"),
        provider=ProviderConfig(type="github", repo="example/repo"),
        scan=ScanConfig(ecosystems=[], auto_detect=True, include_vulnerabilities=False),
        update=UpdateConfig(enabled=True, max_updates=10),
        automation=AutomationConfig(branch_name="depdetective/autoupdate"),
        hooks=HookConfig(),
    )
    report = run_bot(config)

    assert len(report.updates_applied) == 0
    assert report.provider_pr_url is None
    assert fake_provider.called is False
    assert _remote_branch_exists(remote, "depdetective/autoupdate") is False


def test_run_bot_autodetects_node_and_updates_package_json(
    tmp_path: Path,
    monkeypatch,
) -> None:
    remote, work = _init_bare_remote(tmp_path)
    (work / "package.json").write_text(
        json.dumps({"name": "fixture", "dependencies": {"lodash": "^4.17.0"}}, indent=2) + "\n",
        encoding="utf-8",
    )
    _push_main(work, remote)

    fake_provider = _FakeProvider()
    monkeypatch.setattr("depdetective.runner.build_provider", lambda *args, **kwargs: fake_provider)
    monkeypatch.setattr(
        "depdetective.scanners.node_package_json.latest_npm_version",
        lambda _name: "4.17.21",
    )

    config = DepDetectiveConfig(
        repo=RepoConfig(url=str(remote), base_branch="main"),
        provider=ProviderConfig(type="github", repo="example/repo"),
        scan=ScanConfig(ecosystems=[], auto_detect=True, include_vulnerabilities=False),
        update=UpdateConfig(enabled=True, max_updates=10),
        automation=AutomationConfig(branch_name="depdetective/autoupdate"),
        hooks=HookConfig(),
    )
    report = run_bot(config)

    assert len(report.updates_applied) == 1
    assert fake_provider.called is True
    updated = _remote_show_file(remote, "depdetective/autoupdate", "package.json")
    assert '"lodash": "^4.17.21"' in updated


def test_run_bot_dry_run_triggers_workflow_but_does_not_push_or_call_provider(
    tmp_path: Path,
    monkeypatch,
) -> None:
    remote, work = _init_bare_remote(tmp_path)
    (work / "requirements.txt").write_text("requests==2.31.0\n", encoding="utf-8")
    _push_main(work, remote)

    fake_provider = _FakeProvider()
    monkeypatch.setattr(
        "depdetective.scanners.python_requirements.latest_pypi_version",
        lambda _name: "2.32.3",
    )
    monkeypatch.setattr("depdetective.runner.build_provider", lambda *args, **kwargs: fake_provider)

    config = DepDetectiveConfig(
        repo=RepoConfig(url=str(remote), base_branch="main"),
        provider=ProviderConfig(type="github", repo="example/repo"),
        scan=ScanConfig(ecosystems=[], auto_detect=True, include_vulnerabilities=False),
        update=UpdateConfig(enabled=True, max_updates=10),
        automation=AutomationConfig(branch_name="depdetective/autoupdate", dry_run=True),
        hooks=HookConfig(),
    )
    report = run_bot(config)

    assert len(report.updates_applied) == 1
    assert report.pr_workflow_triggered is True
    assert fake_provider.called is False
    assert _remote_branch_exists(remote, "depdetective/autoupdate") is False


def test_run_bot_autodetects_dotnet_and_updates_csproj(
    tmp_path: Path,
    monkeypatch,
) -> None:
    remote, work = _init_bare_remote(tmp_path)
    (work / "App.csproj").write_text(
        """
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
  </ItemGroup>
</Project>
""".strip()
        + "\n",
        encoding="utf-8",
    )
    _push_main(work, remote)

    fake_provider = _FakeProvider()
    monkeypatch.setattr("depdetective.runner.build_provider", lambda *args, **kwargs: fake_provider)
    monkeypatch.setattr(
        "depdetective.scanners.dotnet_nuget.latest_nuget_version",
        lambda _name: "13.0.3",
    )

    config = DepDetectiveConfig(
        repo=RepoConfig(url=str(remote), base_branch="main"),
        provider=ProviderConfig(type="github", repo="example/repo"),
        scan=ScanConfig(ecosystems=[], auto_detect=True, include_vulnerabilities=False),
        update=UpdateConfig(enabled=True, max_updates=10),
        automation=AutomationConfig(branch_name="depdetective/autoupdate"),
        hooks=HookConfig(),
    )
    report = run_bot(config)

    assert len(report.updates_applied) == 1
    assert fake_provider.called is True
    updated = _remote_show_file(remote, "depdetective/autoupdate", "App.csproj")
    assert 'Version="13.0.3"' in updated
