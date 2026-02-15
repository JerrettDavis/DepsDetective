from depdetective.scanners.base import BaseScanner
from depdetective.scanners.dotnet_nuget import DotnetNugetScanner
from depdetective.scanners.go_mod import GoModScanner
from depdetective.scanners.maven_pom import MavenPomScanner
from depdetective.scanners.node_package_json import NodePackageScanner
from depdetective.scanners.python_pyproject import PythonPyprojectScanner
from depdetective.scanners.python_requirements import PythonRequirementsScanner
from depdetective.scanners.rust_cargo import RustCargoScanner

SCANNER_PLUGINS: list[type[BaseScanner]] = [
    GoModScanner,
    MavenPomScanner,
    RustCargoScanner,
    DotnetNugetScanner,
    PythonRequirementsScanner,
    PythonPyprojectScanner,
    NodePackageScanner,
]


def known_ecosystems() -> set[str]:
    return {plugin.ecosystem for plugin in SCANNER_PLUGINS}
