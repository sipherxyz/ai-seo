---
name: aeo-seo-optimize
description: Audit and raise SEO plus AEO/GEO (AI answer engine) scores of a website - robots.txt AI bots, JSON-LD, llms.txt, AI discovery files, Lighthouse SEO. Includes a scoring script with baseline deltas.
---

# AEO/SEO Optimize

Score a page, plan fixes by points gap, ship small PRs, verify on prod, rescore.
Real result: shop.playsipher.com GEO 49 to 94, Lighthouse SEO 92 to 100 (2026-10-23).

## When to Use

- "SEO audit", "AEO", "GEO score", "raise SEO score", "tăng điểm SEO"
- Adding or fixing `llms.txt`, JSON-LD, AI crawler rules in robots.txt, sitemap, canonical, meta
- Making a site readable and citable by ChatGPT, Claude, Perplexity, Gemini, Google AI features

## Score

```bash
S=~/.claude/skills/aeo-seo-optimize/scripts/score.py
python3 $S --url https://example.com/page --out /tmp/aeo-1                       # baseline
python3 $S --url https://example.com/page --out /tmp/aeo-2 --baseline /tmp/aeo-1/report.json   # rescore + deltas
python3 $S --url http://localhost:3000/ --out /tmp/aeo-local --allow-local --no-lighthouse     # local
```

- `--baseline` takes a previous `report.json` or a raw `geo audit --format json` file.
- Needs `uvx` and (for Lighthouse) `npx` + Chrome. `--no-lighthouse` skips it.
- `--allow-local` is loopback only (localhost, 127.0.0.1, ::1). Host-gated checks (robots, canonical, absolute URLs) drop on localhost. Never compare a local score with a prod baseline.
- Output: `report.json`, `report.md` (points per category, gaps sorted by recoverable points, own-check issues, bot table, well-known file table).

Max points: google_ai 20, robots 14, schema 14, content 14, brand_entity 12, meta 11, llms 6, signals 6, ai_discovery 3.

## Workflow

1. **Baseline.** Run score.py on the 2-3 most important public URLs (home, a catalogue page). Keep the out dirs.
2. **Plan by gap.** Read `report.md` "Gaps by recoverable points". Open `references/playbook.md` for each gap. Group into small PRs, cheapest points first (static files, robots, meta), then schema, then rendering fixes. Split off-site items for people (see playbook).
3. **Implement in small PRs.** One theme per PR (robots, JSON-LD, AI files, hidden text). Facts only; copy from existing site data.
4. **Verify on prod** after deploy, not on the PR preview. Use the curl checklist below. Purge the CDN cache for robots.txt and changed pages.
5. **Rescore** with `--baseline` and put the delta table in the PR or issue. Repeat from step 2 for the remaining gaps.

## Curl checklist (prod)

```bash
U=https://example.com
curl -sI $U/robots.txt | rg -i 'HTTP|cf-cache|age|content-type'
for p in /llms.txt /llms-full.txt /.well-known/ai.txt /ai/summary.json /ai/faq.json /ai/service.json /sitemap.xml; do
  printf '%s ' $p; curl -s -o /dev/null -w '%{http_code} %{content_type}\n' $U$p; done
curl -sI -H 'Accept: text/markdown' $U/ | rg -i 'content-type|vary|cache-control'
curl -s $U/page | rg -c 'application/ld\+json'          # JSON-LD blocks
curl -s $U/page | rg -o '<h1' | wc -l                     # want 1
curl -s -A 'GPTBot' $U/page | wc -c                       # same HTML as a browser UA (no cloaking)
```

## Rules

- Facts only. Never invent sameAs URLs, addresses, ratings, reviews, or dates.
- Same HTML for bots and people. No cloaking. Visible text must match JSON-LD.
- Never block Googlebot or Bingbot. Allow search and citation bots (OAI-SearchBot, Claude-SearchBot, PerplexityBot).
- Per-bot robots groups must repeat the private Disallow paths.
- New pages must be public routes (auth guards can redirect signed-out crawlers).
- SSR or ISR the content so crawlers see it without running JS.
- Do not touch legal-restricted content (for example products legal does not allow in markup).
- Rescore on prod after each deploy; a green PR preview proves nothing about CDN or rewrites.
- Do not redirect /about elsewhere.

## Pointers

- `references/playbook.md`: what moves points and how, per category, with pitfalls.
- `scripts/score.py`: scorer (read its USAGE docstring).
- geo-optimizer source (rules behind the score): `~/.cache/uv/archive-v0/*/lib/python3.12/site-packages/geo_optimizer`.
