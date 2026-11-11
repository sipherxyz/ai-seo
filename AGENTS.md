# AGENTS.md

## GitHub Actions runners (cost)

- This repository is public. GitHub-hosted standard runners (`ubuntu-latest`) are free for public repositories, so Linux jobs stay on `ubuntu-latest`.
- Do not use `amd-runner-set` or other self-hosted runners here: pull requests from forks can run code on them.
- Do not add `windows-*`, `macos-*`, or larger runners without DevOps approval. Contact DevOps (vu.truongduc) first.
