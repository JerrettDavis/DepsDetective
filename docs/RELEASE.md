# Release Guide

## GitHub (GHCR)

Included workflow: `.github/workflows/release-image.yml`

- Trigger: tags `v*` or manual dispatch
- Output image: `ghcr.io/<owner>/depdetective`
- Tag and push release:
  - `git tag v0.1.0`
  - `git push origin v0.1.0`

## GitLab Container Registry

Template: `examples/ci/gitlab-release-image.yml`

- Requires `docker:dind` enabled runner
- Uses `$CI_REGISTRY`, `$CI_REGISTRY_USER`, `$CI_REGISTRY_PASSWORD`
- Pushes `${CI_REGISTRY_IMAGE}/depdetective:$CI_COMMIT_TAG`

## Azure DevOps + ACR

Template: `examples/ci/azure-pipelines-release-image.yml`

- Requires an Azure DevOps Docker service connection to ACR
- Tag-based release trigger (`v*`)
- Pushes image to configured ACR repository

## Runtime Deployment

Provider-specific runtime templates:

- GitHub: `examples/ci/github-actions-depdetective.yml`
- GitLab: `examples/ci/gitlab-ci-depdetective.yml`
- Azure DevOps: `examples/ci/azure-pipelines-depdetective.yml`

For pre-production validation, set `automation.dry_run: true` in config to verify scan/update/PR trigger paths without mutating remotes.

## Dogfooding

Workflow: `.github/workflows/dogfood.yml`

- Pull requests run dry-run dogfooding against this repository.
- Scheduled runs execute autonomous mode against this repository.

Provider-specific bot configs:

- GitHub: `examples/configs/github.yml`
- GitLab: `examples/configs/gitlab.yml`
- Azure DevOps: `examples/configs/azure-devops.yml`
