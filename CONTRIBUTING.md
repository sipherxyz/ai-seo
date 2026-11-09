# Contributing

Thanks for helping. Outside contributions are welcome.

## How to contribute

1. Open an issue first for anything bigger than a typo, so we can agree on the change.
2. Fork the repo and create a branch from `main` (`feat/...`, `fix/...`, `docs/...`).
3. Keep each pull request small and on one topic.
4. Run the local checks below.
5. Open a pull request to `main` and fill in the template.

A maintainer reviews every pull request. CI must pass, and one approval from a code owner is needed before merge.
Pull requests are merged with squash.

## Local checks

```bash
python3 -m py_compile skills/*/scripts/*.py
python3 skills/aeo-seo-optimize/scripts/score.py --help
for f in .claude-plugin/*.json; do python3 -m json.tool "$f" >/dev/null; done
```

## Adding or changing a skill

- One folder per skill under `skills/<skill-name>/` with a `SKILL.md` (YAML front matter: `name`, `description`).
- Keep `SKILL.md` short. Put long material in `references/` and code in `scripts/`.
- Scripts: Python 3 standard library only, `argparse` for parameters, a `USAGE` docstring at the top.
- Facts only. Do not add invented scores, URLs, or results.

## Rules

- Never commit secrets, tokens, API keys, internal URLs, or personal data.
- Do not add new third-party dependencies without discussing them in an issue.
- Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages, for example `feat(score): add hreflang check`.
- By contributing, you agree that your contribution is licensed under the [MIT License](LICENSE).

## Security issues

Do not open a public issue for a vulnerability. See [SECURITY.md](SECURITY.md).
