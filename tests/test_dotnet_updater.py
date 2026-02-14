from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.updaters.dotnet_nuget import DotnetNugetUpdater


def test_updates_csproj_and_directory_packages_props(tmp_path: Path) -> None:
    csproj = tmp_path / "App.csproj"
    csproj.write_text(
        """
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="13.0.1" />
  </ItemGroup>
</Project>
""".strip()
        + "\n",
        encoding="utf-8",
    )
    props = tmp_path / "Directory.Packages.props"
    props.write_text(
        """
<Project>
  <ItemGroup>
    <PackageVersion Include="Serilog" Version="3.0.0" />
  </ItemGroup>
</Project>
""".strip()
        + "\n",
        encoding="utf-8",
    )

    deps = [
        DependencyRecord(
            ecosystem="dotnet",
            name="Newtonsoft.Json",
            file_path="App.csproj",
            current_spec="13.0.1",
            resolved_version="13.0.1",
            latest_version="13.0.3",
            section="PackageReference",
        ),
        DependencyRecord(
            ecosystem="dotnet",
            name="Serilog",
            file_path="Directory.Packages.props",
            current_spec="3.0.0",
            resolved_version="3.0.0",
            latest_version="3.1.0",
            section="PackageVersion",
        ),
    ]

    updater = DotnetNugetUpdater()
    changes = updater.apply_updates(tmp_path, deps, max_updates=10)
    assert len(changes) == 2
    assert 'Version="13.0.3"' in csproj.read_text(encoding="utf-8")
    assert 'Version="3.1.0"' in props.read_text(encoding="utf-8")


def test_updates_packages_config(tmp_path: Path) -> None:
    packages = tmp_path / "packages.config"
    packages.write_text(
        """
<packages>
  <package id="NUnit" version="1.0.0" targetFramework="net48" />
</packages>
""".strip()
        + "\n",
        encoding="utf-8",
    )

    deps = [
        DependencyRecord(
            ecosystem="dotnet",
            name="NUnit",
            file_path="packages.config",
            current_spec="1.0.0",
            resolved_version="1.0.0",
            latest_version="2.0.0",
            section="packages.config",
        )
    ]
    updater = DotnetNugetUpdater()
    changes = updater.apply_updates(tmp_path, deps, max_updates=10)
    assert len(changes) == 1
    assert 'version="2.0.0"' in packages.read_text(encoding="utf-8")

