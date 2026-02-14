# Architecture

DepDetective follows a plugin-centered design:

- `scanners/`: discover and parse dependency manifests.
- `updaters/`: apply version changes to manifests.
- `providers/`: open or update PR/MR objects on hosted providers (GitHub, GitLab, Azure DevOps).
- `gitops.py`: provider-agnostic clone/branch/commit/push operations.
- `security.py`: vulnerability enrichment (OSV currently).

## Run flow

1. Load config with optional CLI overrides.
2. Clone the target repo and reset bot branch from base branch.
3. Run `before_scan` hooks.
4. Auto-detect enabled ecosystems from known scanner plugins and discovered files.
5. Run scanners for enabled ecosystems.
6. Run `after_scan` hooks.
7. Query latest versions and (optionally) vulnerability metadata.
8. Run `before_update` hooks.
9. Apply updates through updater plugins.
10. Run `after_update` hooks.
11. Commit and force-push to bot branch.
12. Create or update PR/MR if provider adapter is configured.
13. Emit JSON summary for machine consumption.

## Extensibility contract

To add ecosystem support:

1. Implement `BaseScanner` and `BaseUpdater`.
2. Register implementations in scanner/updater registries.
3. Add tests for parser and updater behavior.

To add provider support:

1. Implement `BaseProvider.open_or_update_pr(...)`.
2. Add adapter selection in `providers/__init__.py`.
