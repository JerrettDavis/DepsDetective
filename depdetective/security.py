from __future__ import annotations

from depdetective.models import DependencyRecord, Vulnerability
from depdetective.registry_clients import osv_query

ECOSYSTEM_MAP = {
    "python": "PyPI",
    "node": "npm",
}


def enrich_vulnerabilities(records: list[DependencyRecord]) -> None:
    for record in records:
        ecosystem = ECOSYSTEM_MAP.get(record.ecosystem)
        if not ecosystem or not record.resolved_version:
            continue
        vulns = osv_query(
            package=record.name,
            ecosystem=ecosystem,
            version=record.resolved_version,
        )
        mapped = []
        for vuln in vulns:
            vuln_id = vuln.get("id", "unknown")
            refs = vuln.get("references", [])
            mapped.append(
                Vulnerability(
                    source="osv",
                    vuln_id=vuln_id,
                    summary=vuln.get("summary"),
                    severity=_extract_severity(vuln),
                    reference=refs[0].get("url") if refs else None,
                )
            )
        record.vulnerabilities = mapped


def _extract_severity(vuln: dict) -> str | None:
    sev = vuln.get("severity", [])
    if not sev:
        return None
    first = sev[0]
    if isinstance(first, dict):
        return first.get("score")
    return str(first)

