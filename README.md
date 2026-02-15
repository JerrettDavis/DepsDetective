# DepDetective

DepDetective is a dependency automation bot similar to Dependabot, built for FOSS and designed for:

- Dockerized execution in CI/CD pipelines
- Direct local execution without containers
- Provider-native PR/MR automation (GitHub, GitLab, Azure DevOps) and generic git fallback
- Pluggable scanners/updaters for ecosystem extensibility
- Zero-specialized credentials (only provider tokens)

## Current capabilities

- Clone repository from URL
- Detect Python (`requirements.txt`, `pyproject.toml`), Node (`package.json`), .NET/NuGet (`*.csproj`, `*.fsproj`, `*.vbproj`, `*.props`, `*.targets`, `Directory.Packages.props`, `packages.config`), Go (`go.mod`), Maven (`pom.xml`), and Rust (`Cargo.toml`) dependencies
- Check latest versions using public registries (PyPI, npm)
- Scan pinned dependency versions against OSV (no API key)
- Apply dependency updates
- Create or update a single rolling PR/MR branch (`depdetective/autoupdate` by default)

## Quick start (direct run)

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
pip install -e .[dev]
depdetective run --repo-url https://github.com/OWNER/REPO.git --provider github --provider-repo OWNER/REPO
```

PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
depdetective run --repo-url https://github.com/OWNER/REPO.git --provider github --provider-repo OWNER/REPO
```

Token environment variables:

- `GITHUB_TOKEN` for GitHub
- `GITLAB_TOKEN` for GitLab
- `AZURE_DEVOPS_TOKEN` or `SYSTEM_ACCESSTOKEN` for Azure DevOps

`--provider-repo` is optional when `--repo-url` includes owner/repo.
For Azure DevOps, `provider.repo` format is `ORG/PROJECT/REPO`.

## Quick start (Docker)

```bash
docker build -t ghcr.io/YOUR_ORG/depdetective:local .
docker run --rm \
  -e GITHUB_TOKEN=$GITHUB_TOKEN \
  ghcr.io/YOUR_ORG/depdetective:local \
  run --repo-url https://github.com/OWNER/REPO.git --provider github --provider-repo OWNER/REPO
```

## Configuration file

Create `depdetective.yml`:

```yaml
repo:
  url: https://github.com/OWNER/REPO.git
  base_branch: main  # optional; auto-detected when omitted

provider:
  type: github  # github | gitlab | azure_devops | generic
  repo: OWNER/REPO
  token_env: GITHUB_TOKEN
  host: null

scan:
  ecosystems: []   # empty + auto_detect=true means "scan everything recognized"
  auto_detect: true
  include_vulnerabilities: true

update:
  enabled: true
  max_updates: 50

automation:
  branch_name: depdetective/autoupdate
  pr_title: "chore(deps): automated dependency updates"
  labels: ["dependencies", "security"]
  dry_run: false

hooks:
  before_scan: []
  after_scan: []
  before_update: []
  after_update: []
```

Run:

```bash
depdetective run --config depdetective.yml
```

Zero-config-ish run (no file):

```bash
depdetective run --repo-url https://github.com/OWNER/REPO.git --provider github
```

GitLab:

```bash
depdetective run --repo-url https://gitlab.com/group/repo.git --provider gitlab
```

Azure DevOps:

```bash
depdetective run --repo-url https://dev.azure.com/ORG/PROJECT/_git/REPO --provider azure_devops
```

Dry-run (no push, no PR/MR API call, but full scan/update planning):

```bash
depdetective run --config depdetective.yml --dry-run
```

## Extending

Add a new ecosystem by implementing:

- `depdetective.scanners.base.BaseScanner`
- `depdetective.updaters.base.BaseUpdater`

Then register classes in:

- `depdetective/scanners/__init__.py`
- `depdetective/updaters/__init__.py`

Hooks are available to run custom commands around bot phases for ecosystems not yet first-class:

- `hooks.before_scan`
- `hooks.after_scan`
- `hooks.before_update`
- `hooks.after_update`

## Release container to GHCR

GitHub Actions workflow included:

- `.github/workflows/ci.yml`
- `.github/workflows/release-image.yml`
- `.github/workflows/dogfood.yml`

The release workflow publishes `ghcr.io/<owner>/depdetective` on tags (`v*`) and manual dispatch.

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/CONFIG_REFERENCE.md`
- `docs/CI_EXAMPLES.md`
- `docs/RELEASE.md`
- `examples/configs/`
- `examples/ci/`

Provider-ready config templates:

- `examples/configs/github.yml`
- `examples/configs/gitlab.yml`
- `examples/configs/azure-devops.yml`

## Dogfooding

This repository dogfoods DepDetective on itself via `.github/workflows/dogfood.yml`:

- `pull_request`: dry-run verification (no push, no PR API calls)
- `schedule`: autonomous mode (pushes bot branch, opens/updates PR)

## Current limitations

- Python updates currently target `requirements*.txt` pinned specs (`==`) and compatible `pyproject.toml` sections.
- Node updates currently target `package.json` (`dependencies`, `devDependencies`).
- .NET updates currently target literal NuGet versions in project/package manifests (`*.csproj`, `*.fsproj`, `*.vbproj`, `*.props`, `*.targets`, `Directory.Packages.props`, `packages.config`).
- Go updates currently target literal versions in `go.mod` `require` statements.
- Maven updates currently target literal `<version>` values in `pom.xml` dependencies.
- Rust updates currently target version-bearing entries in `Cargo.toml` dependency tables.
- Lockfile-aware workflows and grouped update strategies are planned next.
