from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.updaters.go_mod import GoModUpdater


def test_updates_go_mod_requirements(tmp_path: Path) -> None:
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
    deps = [
        DependencyRecord(
            ecosystem="go",
            name="github.com/pkg/errors",
            file_path="go.mod",
            current_spec="v0.8.1",
            resolved_version="v0.8.1",
            latest_version="v0.9.1",
            section="require",
        ),
        DependencyRecord(
            ecosystem="go",
            name="github.com/sirupsen/logrus",
            file_path="go.mod",
            current_spec="v1.8.0",
            resolved_version="v1.8.0",
            latest_version="v1.9.3",
            section="require",
        ),
    ]

    updater = GoModUpdater()
    changes = updater.apply_updates(tmp_path, deps, max_updates=10)
    assert len(changes) == 2
    updated = go_mod.read_text(encoding="utf-8")
    assert "github.com/pkg/errors v0.9.1" in updated
    assert "github.com/sirupsen/logrus v1.9.3" in updated

