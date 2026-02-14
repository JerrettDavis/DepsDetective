from depdetective.runner import _resolve_enabled_ecosystems


def test_resolve_enabled_ecosystems_auto_detect_adds_detected() -> None:
    enabled = _resolve_enabled_ecosystems(
        ecosystems=[],
        auto_detect=True,
        detected={"python", "node"},
    )
    assert enabled == ["node", "python"]


def test_resolve_enabled_ecosystems_explicit_only() -> None:
    enabled = _resolve_enabled_ecosystems(
        ecosystems=["python"],
        auto_detect=False,
        detected={"python", "node"},
    )
    assert enabled == ["python"]

