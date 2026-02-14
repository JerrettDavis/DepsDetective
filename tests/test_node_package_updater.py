import json
from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.updaters.node_package_json import NodePackageUpdater


def test_updates_dependency_with_prefix(tmp_path: Path) -> None:
    package_json = tmp_path / "package.json"
    package_json.write_text(
        json.dumps({"dependencies": {"lodash": "^4.17.0"}}, indent=2),
        encoding="utf-8",
    )
    deps = [
        DependencyRecord(
            ecosystem="node",
            name="lodash",
            file_path="package.json",
            current_spec="^4.17.0",
            resolved_version="4.17.0",
            latest_version="4.17.21",
            section="dependencies",
        )
    ]
    updater = NodePackageUpdater()
    changes = updater.apply_updates(tmp_path, deps, max_updates=10)
    assert len(changes) == 1
    payload = json.loads(package_json.read_text(encoding="utf-8"))
    assert payload["dependencies"]["lodash"] == "^4.17.21"

