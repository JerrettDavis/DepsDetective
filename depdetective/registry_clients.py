from __future__ import annotations

import logging
from urllib.parse import quote

import requests

LOGGER = logging.getLogger(__name__)


def latest_pypi_version(package: str, timeout: int = 20) -> str | None:
    url = f"https://pypi.org/pypi/{quote(package)}/json"
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            return None
        payload = response.json()
        return payload.get("info", {}).get("version")
    except requests.RequestException:
        LOGGER.warning("Failed to query PyPI for %s", package)
        return None


def latest_npm_version(package: str, timeout: int = 20) -> str | None:
    url = f"https://registry.npmjs.org/{quote(package)}"
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            return None
        payload = response.json()
        return payload.get("dist-tags", {}).get("latest")
    except requests.RequestException:
        LOGGER.warning("Failed to query npm for %s", package)
        return None


def latest_nuget_version(package: str, timeout: int = 20) -> str | None:
    package_id = package.lower()
    url = f"https://api.nuget.org/v3-flatcontainer/{quote(package_id)}/index.json"
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            return None
        payload = response.json()
        versions = payload.get("versions", [])
        if not isinstance(versions, list) or not versions:
            return None
        stable_versions = [str(version) for version in versions if "-" not in str(version)]
        candidates = stable_versions or [str(version) for version in versions]
        return candidates[-1] if candidates else None
    except requests.RequestException:
        LOGGER.warning("Failed to query NuGet for %s", package)
        return None


def latest_go_version(module: str, timeout: int = 20) -> str | None:
    url = f"https://proxy.golang.org/{quote(module, safe='/')}/@latest"
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            return None
        payload = response.json()
        version = payload.get("Version")
        if isinstance(version, str):
            return version
        return None
    except requests.RequestException:
        LOGGER.warning("Failed to query Go module proxy for %s", module)
        return None


def latest_maven_version(group_id: str, artifact_id: str, timeout: int = 20) -> str | None:
    try:
        response = requests.get(
            "https://search.maven.org/solrsearch/select",
            params={
                "q": f'g:"{group_id}" AND a:"{artifact_id}"',
                "rows": 1,
                "wt": "json",
            },
            timeout=timeout,
        )
        if response.status_code != 200:
            return None
        payload = response.json()
        docs = payload.get("response", {}).get("docs", [])
        if not docs:
            return None
        latest = docs[0].get("latestVersion")
        if isinstance(latest, str):
            return latest
        return None
    except requests.RequestException:
        LOGGER.warning("Failed to query Maven Central for %s:%s", group_id, artifact_id)
        return None


def latest_crates_version(crate: str, timeout: int = 20) -> str | None:
    url = f"https://crates.io/api/v1/crates/{quote(crate)}"
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            return None
        payload = response.json()
        newest = payload.get("crate", {}).get("newest_version")
        if isinstance(newest, str):
            return newest
        return None
    except requests.RequestException:
        LOGGER.warning("Failed to query crates.io for %s", crate)
        return None


def osv_query(package: str, ecosystem: str, version: str, timeout: int = 20) -> list[dict]:
    payload = {
        "package": {"name": package, "ecosystem": ecosystem},
        "version": version,
    }
    try:
        response = requests.post("https://api.osv.dev/v1/query", json=payload, timeout=timeout)
        if response.status_code != 200:
            return []
        return response.json().get("vulns", [])
    except requests.RequestException:
        LOGGER.warning("Failed to query OSV for %s@%s", package, version)
        return []
