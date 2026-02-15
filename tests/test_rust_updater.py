from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.updaters.rust_cargo import RustCargoUpdater


def test_updates_cargo_versions(tmp_path: Path) -> None:
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text(
        """
[package]
name = "app"
version = "0.1.0"

[dependencies]
serde = "1.0.200"
tokio = { version = "1.38.0", features = ["rt-multi-thread"] }
""".strip()
        + "\n",
        encoding="utf-8",
    )
    deps = [
        DependencyRecord(
            ecosystem="rust",
            name="serde",
            file_path="Cargo.toml",
            current_spec="1.0.200",
            resolved_version="1.0.200",
            latest_version="1.0.204",
            section="dependencies",
        ),
        DependencyRecord(
            ecosystem="rust",
            name="tokio",
            file_path="Cargo.toml",
            current_spec="1.38.0",
            resolved_version="1.38.0",
            latest_version="1.39.2",
            section="dependencies",
        ),
    ]

    updater = RustCargoUpdater()
    changes = updater.apply_updates(tmp_path, deps, max_updates=10)
    assert len(changes) == 2
    updated = cargo.read_text(encoding="utf-8")
    assert 'serde = "1.0.204"' in updated
    assert 'version = "1.39.2"' in updated

