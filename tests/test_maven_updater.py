from pathlib import Path

from depdetective.models import DependencyRecord
from depdetective.updaters.maven_pom import MavenPomUpdater


def test_updates_literal_pom_dependency_versions(tmp_path: Path) -> None:
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

    deps = [
        DependencyRecord(
            ecosystem="maven",
            name="org.slf4j:slf4j-api",
            file_path="pom.xml",
            current_spec="2.0.12",
            resolved_version="2.0.12",
            latest_version="2.0.13",
            section="dependency",
        ),
        DependencyRecord(
            ecosystem="maven",
            name="junit:junit",
            file_path="pom.xml",
            current_spec="${junit.version}",
            resolved_version=None,
            latest_version="4.13.2",
            section="dependency",
        ),
    ]

    updater = MavenPomUpdater()
    changes = updater.apply_updates(tmp_path, deps, max_updates=10)
    assert len(changes) == 1
    updated = pom.read_text(encoding="utf-8")
    assert "<version>2.0.13</version>" in updated
    assert "<version>${junit.version}</version>" in updated

