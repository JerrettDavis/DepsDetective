from depdetective.scanners.base import BaseScanner
from depdetective.scanners.dotnet_nuget import DotnetNugetScanner
from depdetective.scanners.node_package_json import NodePackageScanner
from depdetective.scanners.python_pyproject import PythonPyprojectScanner
from depdetective.scanners.python_requirements import PythonRequirementsScanner

SCANNER_PLUGINS: list[type[BaseScanner]] = [
    DotnetNugetScanner,
    PythonRequirementsScanner,
    PythonPyprojectScanner,
    NodePackageScanner,
]


def known_ecosystems() -> set[str]:
    return {plugin.ecosystem for plugin in SCANNER_PLUGINS}
