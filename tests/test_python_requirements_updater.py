from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.updaters.python_requirements import PythonRequirementsUpdater


def test_updates_pinned_requirement(tmp_path: Path) -> None:
    req = tmp_path / "requirements.txt"
    req.write_text("requests==2.31.0\n", encoding="utf-8")
    deps = [
        DependencyRecord(
            ecosystem="python",
            name="requests",
            file_path="requirements.txt",
            current_spec="==2.31.0",
            resolved_version="2.31.0",
            latest_version="2.32.3",
        )
    ]
    updater = PythonRequirementsUpdater()
    changes = updater.apply_updates(tmp_path, deps, max_updates=10)
    assert len(changes) == 1
    content = req.read_text(encoding="utf-8")
    assert "requests==2.32.3" in content

