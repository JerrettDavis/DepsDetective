from depdetective.updaters.base import BaseUpdater
from depdetective.updaters.dotnet_nuget import DotnetNugetUpdater
from depdetective.updaters.node_package_json import NodePackageUpdater
from depdetective.updaters.python_pyproject import PythonPyprojectUpdater
from depdetective.updaters.python_requirements import PythonRequirementsUpdater

UPDATER_PLUGINS: list[type[BaseUpdater]] = [
    DotnetNugetUpdater,
    PythonRequirementsUpdater,
    PythonPyprojectUpdater,
    NodePackageUpdater,
]
