from depdetective.config import load_config


def test_load_config_with_overrides() -> None:
    config = load_config(
        None,
        overrides={
            "repo": {"url": "https://example.com/repo.git"},
            "provider": {"type": "generic"},
        },
    )
    assert config.repo.url == "https://example.com/repo.git"
    assert config.repo.base_branch is None
    assert config.provider.type == "generic"
    assert config.scan.auto_detect is True
    assert config.scan.ecosystems == []


def test_load_hooks() -> None:
    config = load_config(
        None,
        overrides={
            "repo": {"url": "https://example.com/repo.git"},
            "hooks": {
                "before_scan": ["echo scanning"],
                "after_update": ["echo done"],
            },
        },
    )
    assert config.hooks.before_scan == ["echo scanning"]
    assert config.hooks.after_update == ["echo done"]
