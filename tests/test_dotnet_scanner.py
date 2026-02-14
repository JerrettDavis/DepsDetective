from pathlib import Path

from depdetective.scanners.dotnet_nuget import DotnetNugetScanner


def test_scans_csproj_and_directory_packages_props(tmp_path: Path, monkeypatch) -> None:
    def fake_latest(package: str) -> str:
        return {
            "Newtonsoft.Json": "13.0.3",
            "Serilog": "3.1.0",
        }.get(package, "1.0.0")

    monkeypatch.setattr("depdetective.scanners.dotnet_nuget.latest_nuget_version", fake_latest)

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

    scanner = DotnetNugetScanner()
    files = scanner.discover_files(tmp_path)
    assert csproj in files
    assert props in files

    records = scanner.scan_file(csproj, tmp_path) + scanner.scan_file(props, tmp_path)
    by_name = {record.name: record for record in records}
    assert by_name["Newtonsoft.Json"].resolved_version == "13.0.1"
    assert by_name["Newtonsoft.Json"].latest_version == "13.0.3"
    assert by_name["Serilog"].resolved_version == "3.0.0"
    assert by_name["Serilog"].latest_version == "3.1.0"


def test_scans_packages_config(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("depdetective.scanners.dotnet_nuget.latest_nuget_version", lambda _name: "2.0.0")

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

    scanner = DotnetNugetScanner()
    records = scanner.scan_file(packages, tmp_path)
    assert len(records) == 1
    assert records[0].name == "NUnit"
    assert records[0].resolved_version == "1.0.0"
    assert records[0].latest_version == "2.0.0"


def test_does_not_resolve_range_versions(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("depdetective.scanners.dotnet_nuget.latest_nuget_version", lambda _name: "13.0.3")

    csproj = tmp_path / "App.csproj"
    csproj.write_text(
        """
<Project Sdk="Microsoft.NET.Sdk">
  <ItemGroup>
    <PackageReference Include="Newtonsoft.Json" Version="[13.0.1,14.0.0)" />
  </ItemGroup>
</Project>
""".strip()
        + "\n",
        encoding="utf-8",
    )

    scanner = DotnetNugetScanner()
    records = scanner.scan_file(csproj, tmp_path)
    assert len(records) == 1
    assert records[0].resolved_version is None
    assert records[0].update_available is False
