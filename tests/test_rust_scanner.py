from pathlib import Path

from depdetective.scanners.rust_cargo import RustCargoScanner


def test_scans_cargo_dependencies(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "depdetective.scanners.rust_cargo.latest_crates_version",
        lambda name: {"serde": "1.0.204", "tokio": "1.39.2", "clap": "4.5.10"}.get(name),
    )
    cargo = tmp_path / "Cargo.toml"
    cargo.write_text(
        """
[package]
name = "app"
version = "0.1.0"

[dependencies]
serde = "1.0.200"
tokio = { version = "1.38.0", features = ["rt-multi-thread"] }

[workspace.dependencies]
clap = "4.5.9"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    scanner = RustCargoScanner()
    records = scanner.scan_file(cargo, tmp_path)
    by_key = {(record.section, record.name): record for record in records}
    assert by_key[("dependencies", "serde")].resolved_version == "1.0.200"
    assert by_key[("dependencies", "serde")].latest_version == "1.0.204"
    assert by_key[("dependencies", "tokio")].resolved_version == "1.38.0"
    assert by_key[("workspace.dependencies", "clap")].latest_version == "4.5.10"

