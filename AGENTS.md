# AGENTS.md

## GitHub Actions runners (cost)

- For Linux jobs, use `runs-on: amd-runner-set`. These are the org self-hosted runners. They do not use the GitHub Actions quota.
- Do not add or move jobs to GitHub-hosted runners (`ubuntu-*`, `windows-*`, `macos-*`) without DevOps approval. These runners use the shared org quota of 3,000 minutes each month. A Windows minute costs about 1.7 times a Linux minute. A macOS minute costs about 10 times a Linux minute. When the quota is used, GitHub-hosted jobs stop until the next month.
- If a job really needs Windows, macOS, or ARM, contact DevOps (vu.truongduc) before you add it. DevOps helps you to find a runner that does not cost money.
- `amd-runner-set` runs each job in a container (Ubuntu 24.04, `myoung34/github-runner`). It has git, docker (with buildx), jq, gh, aws, python3, and node. It does not have yarn, npm, pnpm, terraform, or argocd: install them in the job (for example, with `actions/setup-node` or `hashicorp/setup-terraform`). Jobs that use `services:`, `container:`, or `docker compose` with `localhost` ports are not tested on it: ask DevOps first.
