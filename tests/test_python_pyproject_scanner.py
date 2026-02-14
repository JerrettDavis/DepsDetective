from pathlib import Path

from depdetective.scanners.python_pyproject import PythonPyprojectScanner


def test_scans_project_and_poetry_dependencies(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "depdetective.scanners.python_pyproject.latest_pypi_version",
        lambda _name: "9.9.9",
    )
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
dependencies = ["fastapi==0.111.0"]

[tool.poetry.dependencies]
python = "^3.12"
requests = "^2.31.0"
""".strip()
        + "\n",
        encoding="utf-8",
    )

    scanner = PythonPyprojectScanner()
    records = scanner.scan_file(pyproject, tmp_path)
    names = {(record.name, record.section) for record in records}
    assert ("fastapi", "project.dependencies") in names
    assert ("requests", "tool.poetry.dependencies") in names

