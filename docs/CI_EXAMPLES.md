# CI Examples

## GitHub Actions

```yaml
name: DepDetective
on:
  schedule:
    - cron: "0 5 * * 1"
  workflow_dispatch:

jobs:
  scan-and-update:
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
    steps:
      - name: Run container
        run: |
          docker run --rm \
            -e GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }} \
            ghcr.io/your-org/depdetective:latest \
            run \
            --repo-url https://github.com/your-org/your-repo.git \
            --provider github \
            --provider-repo your-org/your-repo
```

Reference file: `examples/ci/github-actions-depdetective.yml`

Dogfooding workflow for this repository: `.github/workflows/dogfood.yml`

## GitLab CI

```yaml
depdetective:
  image: ghcr.io/your-org/depdetective:latest
  script:
    - depdetective run --config depdetective.yml
  variables:
    GITLAB_TOKEN: $GITLAB_TOKEN
```

Reference file: `examples/ci/gitlab-ci-depdetective.yml`

## Azure DevOps Pipelines

```yaml
steps:
  - task: Bash@3
    env:
      SYSTEM_ACCESSTOKEN: $(System.AccessToken)
    inputs:
      targetType: inline
      script: |
        docker run --rm \
          -e SYSTEM_ACCESSTOKEN="$(System.AccessToken)" \
          ghcr.io/your-org/depdetective:latest \
          run --config examples/configs/azure-devops.yml
```

Reference file: `examples/ci/azure-pipelines-depdetective.yml`

Note: enable "Allow scripts to access the OAuth token" so `$(System.AccessToken)` is populated.

## Generic git provider mode

Use `provider.type: generic` to skip PR/MR API calls while still pushing a bot branch.

For no-mutation validation runs, set `automation.dry_run: true` (or pass `--dry-run`) to skip both push and provider API calls.
