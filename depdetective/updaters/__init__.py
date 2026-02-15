from depdetective.updaters.base import BaseUpdater
from depdetective.updaters.dotnet_nuget import DotnetNugetUpdater
from depdetective.updaters.go_mod import GoModUpdater
from depdetective.updaters.maven_pom import MavenPomUpdater
from depdetective.updaters.node_package_json import NodePackageUpdater
from depdetective.updaters.python_pyproject import PythonPyprojectUpdater
from depdetective.updaters.python_requirements import PythonRequirementsUpdater
from depdetective.updaters.rust_cargo import RustCargoUpdater

UPDATER_PLUGINS: list[type[BaseUpdater]] = [
    GoModUpdater,
    MavenPomUpdater,
    RustCargoUpdater,
    DotnetNugetUpdater,
    PythonRequirementsUpdater,
    PythonPyprojectUpdater,
    NodePackageUpdater,
]
