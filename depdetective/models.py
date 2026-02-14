from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class Vulnerability:
    source: str
    vuln_id: str
    summary: str | None = None
    severity: str | None = None
    reference: str | None = None


@dataclass(slots=True)
class DependencyRecord:
    ecosystem: str
    name: str
    file_path: str
    current_spec: str
    resolved_version: str | None = None
    latest_version: str | None = None
    section: str | None = None
    vulnerabilities: list[Vulnerability] = field(default_factory=list)

    @property
    def update_available(self) -> bool:
        if not self.latest_version or not self.resolved_version:
            return False
        return self.latest_version != self.resolved_version


@dataclass(slots=True)
class UpdateAction:
    ecosystem: str
    file_path: str
    dependency: str
    old_spec: str
    new_spec: str
    latest_version: str


@dataclass(slots=True)
class RunReport:
    scanned_dependencies: list[DependencyRecord] = field(default_factory=list)
    updates_applied: list[UpdateAction] = field(default_factory=list)
    provider_pr_url: str | None = None
    pr_workflow_triggered: bool = False

    @property
    def vulnerabilities_count(self) -> int:
        return sum(len(dep.vulnerabilities) for dep in self.scanned_dependencies)
