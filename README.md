# ai-seo

Agent skills for SEO and AEO/GEO (AI answer engine optimization).

## Skills

| Skill | What it does |
|---|---|
| [`aeo-seo-optimize`](skills/aeo-seo-optimize/SKILL.md) | Score a page (geo-optimizer + Lighthouse SEO + own checks), plan fixes by points gap, verify on prod, rescore with baseline deltas. Covers robots.txt AI bots, JSON-LD, `llms.txt`, AI discovery files, meta. |

Real result: shop.playsipher.com GEO 49 to 94, Lighthouse SEO 92 to 100 (2026-10-23).

## Install

Claude Code plugin:

```
/plugin marketplace add sipherxyz/ai-seo
/plugin install ai-seo@ai-seo
```

Or as a plain skill (keeps the `~/.claude/skills/...` paths in SKILL.md working):

```bash
git clone https://github.com/sipherxyz/ai-seo.git ~/src/ai-seo
ln -s ~/src/ai-seo/skills/aeo-seo-optimize ~/.claude/skills/aeo-seo-optimize
```

## Requirements

- Python 3 (stdlib only)
- `uvx` (runs `geo-optimizer-skill`)
- `npx` + Chrome for Lighthouse (skip with `--no-lighthouse`)

## Quick start

```bash
python3 skills/aeo-seo-optimize/scripts/score.py --url https://example.com/ --out ./aeo-1
python3 skills/aeo-seo-optimize/scripts/score.py --url https://example.com/ --out ./aeo-2 --baseline ./aeo-1/report.json
```

See [SKILL.md](skills/aeo-seo-optimize/SKILL.md) for the workflow and [playbook.md](skills/aeo-seo-optimize/references/playbook.md) for fixes per category.

## Contributing

Contributions are welcome. Read [CONTRIBUTING.md](CONTRIBUTING.md) and the [Code of Conduct](CODE_OF_CONDUCT.md).
Report security problems privately as described in [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
