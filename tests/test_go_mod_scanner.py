from pathlib import Path

from depdetective.scanners.go_mod import GoModScanner


def test_scans_go_mod_requirements(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "depdetective.scanners.go_mod.latest_go_version",
        lambda name: {
            "github.com/pkg/errors": "v0.9.1",
            "github.com/sirupsen/logrus": "v1.9.3",
        }.get(name),
    )
    go_mod = tmp_path / "go.mod"
    go_mod.write_text(
        """
module example.com/app

go 1.22

require github.com/pkg/errors v0.8.1

require (
    github.com/sirupsen/logrus v1.8.0 // indirect
)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    scanner = GoModScanner()
    records = scanner.scan_file(go_mod, tmp_path)
    by_name = {record.name: record for record in records}
    assert by_name["github.com/pkg/errors"].resolved_version == "v0.8.1"
    assert by_name["github.com/pkg/errors"].latest_version == "v0.9.1"
    assert by_name["github.com/sirupsen/logrus"].resolved_version == "v1.8.0"
    assert by_name["github.com/sirupsen/logrus"].latest_version == "v1.9.3"

