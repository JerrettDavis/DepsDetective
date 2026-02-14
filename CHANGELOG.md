# Changelog

## 0.1.0 - 2026-02-14

Initial public release candidate.

- Core dependency scanning and update automation with plugin architecture.
- Ecosystem support:
  - Python: `requirements*.txt`, `pyproject.toml` (project + poetry sections).
  - Node: `package.json` dependencies/devDependencies.
- Vulnerability enrichment via OSV.
- Provider integrations:
  - GitHub pull requests.
  - GitLab merge requests.
  - Azure DevOps pull requests.
  - Generic git fallback.
- Lifecycle hooks for custom command-based integrations.
- Auto-detection of supported ecosystems by discovered manifests.
- Dry-run mode for no-mutation validation.
- Docker packaging and CI/CD templates for GitHub, GitLab, Azure DevOps.
- Dogfooding workflow to run DepDetective on this project itself.

