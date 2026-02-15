from pathlib import Path

from depdetective.scanners.maven_pom import MavenPomScanner


def test_scans_pom_dependencies(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "depdetective.scanners.maven_pom.latest_maven_version",
        lambda g, a: {
            ("org.slf4j", "slf4j-api"): "2.0.13",
            ("junit", "junit"): "4.13.2",
        }.get((g, a)),
    )
    pom = tmp_path / "pom.xml"
    pom.write_text(
        """
<project>
  <dependencies>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
      <version>2.0.12</version>
    </dependency>
    <dependency>
      <groupId>junit</groupId>
      <artifactId>junit</artifactId>
      <version>${junit.version}</version>
    </dependency>
  </dependencies>
</project>
""".strip()
        + "\n",
        encoding="utf-8",
    )

    scanner = MavenPomScanner()
    records = scanner.scan_file(pom, tmp_path)
    by_name = {record.name: record for record in records}
    assert by_name["org.slf4j:slf4j-api"].resolved_version == "2.0.12"
    assert by_name["org.slf4j:slf4j-api"].latest_version == "2.0.13"
    assert by_name["junit:junit"].resolved_version is None

