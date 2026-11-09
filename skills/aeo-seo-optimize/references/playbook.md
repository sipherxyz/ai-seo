# AEO/SEO Playbook

Source: real work on shop.playsipher.com (2026-10-23): GEO 49 to 94, Lighthouse SEO 92 to 100.
Map: category (max points) then what to do. Check the score.py report for which gaps are open.

## robots.txt (14)

- Each per-bot group (GPTBot, ClaudeBot, ...) must repeat the private Disallow paths. A bot that matches its own group ignores the `*` group.
- Allow search and citation bots: OAI-SearchBot, Claude-SearchBot, PerplexityBot, GPTBot, ClaudeBot.
- Google-Extended only controls Gemini grounding and training. It does not affect Search. Never block Googlebot or Bingbot.
- Add a `Sitemap:` line.
- Cloudflare may cache robots.txt for hours. Purge it after each change, then check `cf-cache-status` and `age`.

## Schema / JSON-LD (14)

- Organization: name, url, logo, `sameAs`, `contactPoint`, `description` equal to the meta description.
- WebSite: `author`/`publisher`, `inLanguage`.
- BreadcrumbList on inner pages.
- WebPage with `dateModified` plus a visible "Last updated" line. Use one fixed UTC format with h23 (`Intl.DateTimeFormat` with `hourCycle: 'h23'`, `timeZone: 'UTC'`). Take the date from build or ISR time, not `new Date()` at render, or hydration will mismatch.
- ItemList / Product only for items legal allows.
- FAQPage built from the same data array that the visible FAQ renders. Markup must match visible text.
- Validate that every block parses (score.py reports parse errors and the @type list).

## Brand entity (12)

- Knowledge Graph pillars come only from JSON-LD `sameAs`: Wikipedia, Wikidata, LinkedIn, Crunchbase. Never invent URLs; add only profiles that exist.
- The About check needs a visible `<a href>` containing `/about` on the audited page. A page that is only in the sitemap does not count. Do not redirect /about elsewhere.
- One brand name across title, og:title, h1, JSON-LD.
- Off-site (needs people): Crunchbase, Wikidata, Wikipedia entries, a postal address, articles/RSS, Search Console GenAI controls.

## Content (14) and hidden-text penalty

- SSR/ISR the catalogue text so crawlers see it. One h1 per page.
- Hidden text in SSR HTML is penalised (shows as "Hidden text detected"). Typical causes:
  - Chakra/Radix popovers, menus, tooltips render closed content in SSR: use lazy rendering (`isLazy`, or mount on open).
  - framer-motion `initial={{opacity:0}}` on the page wrapper makes the whole SSR HTML opacity:0: use `initial={false}` on first paint.
  - `display:none` blocks that contain text (mobile/desktop duplicates). Render one.
- score.py lists samples under "hidden text hits".
- Alt text: descriptive for content images; `alt=""` plus `role="presentation"` for decorative ones.

## Meta (11) and signals (6)

- Unique title and meta description, canonical, og tags, `lang`.
- Byline: `<meta name="author">` plus JSON-LD `author`/`publisher` (fixes G-BYLINE).
- Freshness: visible "Last updated" plus `dateModified`.
- Lighthouse SEO fixes: descriptive link text, valid canonical and hreflang, crawlable links, image alt, viewport, robots not blocking.

## llms (6) and AI discovery (3): cheap static points

- `/llms.txt` (short, linked sections) and `/llms-full.txt` (full text). Content-Type text/plain or text/markdown.
- `/.well-known/ai.txt`, `/ai/summary.json`, `/ai/faq.json`, `/ai/service.json`: static files, JSON with correct content-type, facts from the site only.
- Markdown for agents: rewrite requests with `Accept: text/markdown` to a markdown render. Match the whole media type with a strict regex and skip `q=0`. Send `Vary: Accept` and `Cache-Control: private` (so the CDN does not serve markdown to browsers).
- Serve all of these as public routes outside auth middleware and i18n redirects.

## google_ai (20)

- Indexable (no noindex), 200 status, canonical, structured data matching visible text, byline, freshness, helpful content. Read the `[G-*]` codes in the recommendations.

## Review pattern

1. PR per theme, with a before/after score table from `score.py --baseline`.
2. After deploy: curl checklist (SKILL.md), purge CDN, rescore on prod.
3. Compare with the baseline; list remaining gaps and which are off-site.
4. Check the HTML for bots and browsers is identical (no cloaking).
