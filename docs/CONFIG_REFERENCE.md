# Config Reference

`depdetective.yml` schema:

```yaml
repo:
  url: <required git clone url>
  base_branch: main             # optional; auto-detected when omitted
  clone_dir: /tmp/depdetective-run

provider:
  type: github|gitlab|azure_devops|generic
  repo: OWNER/REPO            # github
  # repo: group/subgroup/repo # gitlab
  # repo: ORG/PROJECT/REPO    # azure_devops
  token_env: GITHUB_TOKEN     # defaults by provider
  host: null                  # optional API host override

scan:
  ecosystems: []                # optional explicit list (e.g. [python, node, dotnet])
  auto_detect: true             # auto-enable ecosystems with matching manifests
  include_vulnerabilities: true

update:
  enabled: true
  max_updates: 50

automation:
  branch_name: depdetective/autoupdate
  pr_title: "chore(deps): automated dependency updates"
  pr_body_template: null
  labels: [dependencies, security]
  rebase_existing: true
  dry_run: false              # when true, skips push + provider API calls

hooks:
  before_scan: []
  after_scan: []
  before_update: []
  after_update: []
```

## CLI overrides

CLI flags may replace config values:

- `--repo-url`
- `--base-branch`
- `--provider`
- `--provider-repo`
- `--provider-token-env`
- `--provider-host`
- `--dry-run`
- `--ecosystem` (repeatable)
- `--auto-detect` / `--no-auto-detect`
- `--report-path`
