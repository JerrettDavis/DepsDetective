from depdetective.cli import _build_overrides, build_parser


def test_base_branch_not_forced_when_not_provided() -> None:
    parser = build_parser()
    args = parser.parse_args(["run", "--repo-url", "https://example.com/repo.git"])
    overrides = _build_overrides(args)
    assert overrides["repo"]["url"] == "https://example.com/repo.git"
    assert "base_branch" not in overrides["repo"]


def test_ecosystem_overrides() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "run",
            "--repo-url",
            "https://example.com/repo.git",
            "--ecosystem",
            "python",
            "--ecosystem",
            "node",
            "--no-auto-detect",
        ]
    )
    overrides = _build_overrides(args)
    assert overrides["scan"]["ecosystems"] == ["python", "node"]
    assert overrides["scan"]["auto_detect"] is False


def test_provider_host_override() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "run",
            "--repo-url",
            "https://example.com/repo.git",
            "--provider",
            "azure_devops",
            "--provider-host",
            "https://dev.azure.com",
        ]
    )
    overrides = _build_overrides(args)
    assert overrides["provider"]["type"] == "azure_devops"
    assert overrides["provider"]["host"] == "https://dev.azure.com"


def test_dry_run_override() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "run",
            "--repo-url",
            "https://example.com/repo.git",
            "--dry-run",
        ]
    )
    overrides = _build_overrides(args)
    assert overrides["automation"]["dry_run"] is True
