from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.updaters.python_pyproject import PythonPyprojectUpdater


def test_updates_project_and_poetry_specs(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
dependencies = ["fastapi==0.100.0"]

[tool.poetry.dependencies]
python = "^3.12"
requests = "^2.31.0"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    deps = [
        DependencyRecord(
            ecosystem="python",
            name="fastapi",
            file_path="pyproject.toml",
            current_spec="==0.100.0",
            resolved_version="0.100.0",
            latest_version="0.111.0",
            section="project.dependencies",
        ),
        DependencyRecord(
            ecosystem="python",
            name="requests",
            file_path="pyproject.toml",
            current_spec="^2.31.0",
            resolved_version="2.31.0",
            latest_version="2.32.3",
            section="tool.poetry.dependencies",
        ),
    ]
    updater = PythonPyprojectUpdater()
    changes = updater.apply_updates(tmp_path, deps, max_updates=10)
    assert len(changes) == 2
    updated = pyproject.read_text(encoding="utf-8")
    assert "fastapi==0.111.0" in updated
    assert 'requests = "^2.32.3"' in updated

