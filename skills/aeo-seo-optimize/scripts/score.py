#!/usr/bin/env python3
"""
USAGE:
  python3 score.py --url <page> [--out <dir>] [--baseline <prev.json>]
                   [--no-lighthouse] [--allow-local]

Scores SEO + AEO/GEO of one page. Python 3 stdlib only; shells out to
  - `uvx --from geo-optimizer-skill geo audit --url <url> --format json`
  - `npx -y lighthouse <url> --only-categories=seo ...`  (skip: --no-lighthouse)
and adds its own fetch-based checks (JSON-LD, h1, canonical, robots AI bots,
well-known AI files, text/markdown, hidden text, image alt).

Writes <out>/report.json and <out>/report.md (default out: ./aeo-report) and
prints a short summary. --baseline accepts a previous report.json OR a raw
`geo audit --format json` file and prints deltas.

--allow-local: geo-optimizer refuses localhost (SSRF guard in
geo_optimizer.utils.validators). With this flag the audit runs through a small
wrapper that, inside the geo process only, un-blocks the hostnames
localhost/127.0.0.1/[::1] and the loopback IPs 127.0.0.0/8 and ::1. All other
private/metadata ranges stay blocked. Host-gated checks (robots, canonical,
absolute URLs) differ on localhost; compare only against a localhost baseline.
"""
import argparse, json, os, re, subprocess, sys, urllib.error, urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse, urljoin

CATS = {"google_ai": 20, "robots": 14, "schema": 14, "content": 14, "brand_entity": 12,
        "meta": 11, "llms": 6, "signals": 6, "ai_discovery": 3}
BOTS = ["GPTBot", "ClaudeBot", "Claude-SearchBot", "OAI-SearchBot", "PerplexityBot",
        "Google-Extended", "Googlebot", "Bingbot"]
WELL_KNOWN = ["/llms.txt", "/llms-full.txt", "/.well-known/ai.txt", "/ai/summary.json",
              "/ai/faq.json", "/ai/service.json", "/sitemap.xml"]
UA = "Mozilla/5.0 (compatible; aeo-seo-optimize/1.0)"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

# Runs inside the uvx env (geo-optimizer-skill installed). Loopback-only opt-in.
WRAPPER = r'''
import sys, ipaddress
import geo_optimizer.utils.validators as v
v._BLOCKED_HOSTNAMES.discard("localhost")
_orig = v._check_ip_blocked
def _patched(ip):
    try:
        if ipaddress.ip_address(ip).is_loopback:
            return False, None
    except ValueError:
        pass
    return _orig(ip)
v._check_ip_blocked = _patched
from geo_optimizer.cli.main import cli
cli(sys.argv[1:], standalone_mode=True)
'''


def run(cmd, timeout=420):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError as e:
        return 127, "", str(e)
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"


def fetch(url, accept=None, timeout=25):
    h = {"User-Agent": UA}
    if accept:
        h["Accept"] = accept
    req = urllib.request.Request(url, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read(3_000_000).decode("utf-8", "replace")
            return r.status, {k.lower(): v for k, v in r.headers.items()}, body
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, ""
    except Exception as e:  # network/DNS/TLS
        return 0, {"error": str(e)}, ""


# ---------- a) geo-optimizer ----------
def geo_audit(url, allow_local):
    if allow_local:
        cmd = ["uvx", "--from", "geo-optimizer-skill", "python", "-c", WRAPPER,
               "audit", "--url", url, "--format", "json"]
    else:
        cmd = ["uvx", "--from", "geo-optimizer-skill", "geo", "audit", "--url", url, "--format", "json"]
    rc, out, err = run(cmd)
    try:
        d = json.loads(out[out.index("{"):])
    except Exception:
        return {"error": f"geo audit failed rc={rc}: {(err or out)[-400:]}"}
    return {k: d.get(k) for k in ("score", "band", "score_max", "score_breakdown", "recommendations",
                                  "recommendations_by_category", "http_status", "error")}


# ---------- b) lighthouse ----------
def lighthouse(url):
    rc, out, err = run(["npx", "-y", "lighthouse", url, "--only-categories=seo",
                        "--chrome-flags=--headless=new", "--output=json", "--quiet"], timeout=600)
    try:
        d = json.loads(out[out.index("{"):])
        seo = d["categories"]["seo"]
        failed = [{"id": r["id"], "title": d["audits"][r["id"]]["title"]}
                  for r in seo["auditRefs"]
                  if d["audits"][r["id"]].get("score") is not None and d["audits"][r["id"]]["score"] < 1]
        return {"seo": round(seo["score"] * 100), "failed": failed}
    except Exception:
        return {"error": f"lighthouse failed rc={rc}: {(err or out)[-300:]}"}


# ---------- c) own checks ----------
class Page(HTMLParser):
    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.h1 = 0; self.canonical = None; self.meta = {}; self.ld = []; self.imgs_no_alt = 0
        self.imgs = 0; self.stack = []; self.hidden_text = []; self._ld = False; self._buf = []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h1": self.h1 += 1
        if tag == "link" and "canonical" in (a.get("rel") or "").lower(): self.canonical = a.get("href")
        if tag == "meta" and a.get("name"): self.meta[a["name"].lower()] = a.get("content", "")
        if tag == "meta" and a.get("property"): self.meta[a["property"].lower()] = a.get("content", "")
        if tag == "img":
            self.imgs += 1
            if "alt" not in a: self.imgs_no_alt += 1
        if tag == "script":
            self._ld = (a.get("type") or "").lower() == "application/ld+json"; self._buf = []
            self.skip += 1
            return
        if tag == "style": self.skip += 1; return
        if tag in self.VOID: return
        st = (a.get("style") or "").lower().replace(" ", "")
        hid = bool(re.search(r"opacity:0(?![.\d])|display:none", st)) or "hidden" in a
        self.stack.append((tag, hid))

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            if tag == "script" and self._ld: self.ld.append("".join(self._buf)); self._ld = False
            self.skip = max(0, self.skip - 1)
            return
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]; break

    def handle_data(self, data):
        if self._ld: self._buf.append(data); return
        if self.skip: return
        t = data.strip()
        if t and any(h for _, h in self.stack): self.hidden_text.append(t[:60])


def ld_types(blocks):
    types, bad = [], 0

    def walk(o):
        if isinstance(o, list):
            for x in o: walk(x)
        elif isinstance(o, dict):
            t = o.get("@type")
            if t: types.extend(t if isinstance(t, list) else [t])
            for v in o.values():
                if isinstance(v, (list, dict)): walk(v)
    for b in blocks:
        try: walk(json.loads(b))
        except Exception: bad += 1
    return sorted(set(map(str, types))), bad


def parse_robots(txt):
    groups, cur, seen_rule = [], None, False
    for line in txt.splitlines():
        line = line.split("#")[0].strip()
        if ":" not in line: continue
        k, v = [x.strip() for x in line.split(":", 1)]
        k = k.lower()
        if k == "user-agent":
            if cur is None or seen_rule: cur = {"agents": [], "dis": [], "allow": []}; groups.append(cur); seen_rule = False
            cur["agents"].append(v.lower())
        elif k in ("disallow", "allow") and cur is not None:
            seen_rule = True
            cur["dis" if k == "disallow" else "allow"].append(v)
    return groups


def bot_status(groups, bot):
    g = next((x for x in groups if bot.lower() in x["agents"]), None) or \
        next((x for x in groups if "*" in x["agents"]), None)
    if g is None: return "allowed (no group)"
    if "/" in g["dis"] and "/" not in g["allow"]: return "BLOCKED"
    n = len([d for d in g["dis"] if d])
    return f"allowed ({n} disallow rules)" if n else "allowed"


def own_checks(url):
    p = urlparse(url); base = f"{p.scheme}://{p.netloc}"
    res = {}
    st, hd, html = fetch(url)
    res["page"] = {"status": st, "content_type": hd.get("content-type"), "bytes": len(html)}
    pg = Page()
    try: pg.feed(html)
    except Exception: pass
    types, bad = ld_types(pg.ld)
    res["html"] = {"jsonld_blocks": len(pg.ld), "jsonld_parse_errors": bad, "jsonld_types": types,
                   "h1_count": pg.h1, "canonical": pg.canonical,
                   "meta_description": bool(pg.meta.get("description")),
                   "meta_author": pg.meta.get("author"),
                   "hidden_text_hits": len(pg.hidden_text), "hidden_text_samples": pg.hidden_text[:5],
                   "images": pg.imgs, "images_missing_alt": pg.imgs_no_alt}
    st, hd, txt = fetch(base + "/robots.txt")
    groups = parse_robots(txt) if st == 200 else []
    res["robots"] = {"status": st, "cf_cache_status": hd.get("cf-cache-status"), "age": hd.get("age"),
                     "bots": {b: bot_status(groups, b) for b in BOTS} if st == 200 else {},
                     "sitemap_directive": bool(re.search(r"(?im)^\s*sitemap:", txt))}
    wk = {}
    for path in WELL_KNOWN:
        st, hd, body = fetch(base + path)
        wk[path] = {"status": st, "content_type": hd.get("content-type"), "bytes": len(body)}
    res["well_known"] = wk
    st, hd, _ = fetch(url, accept="text/markdown")
    ct = hd.get("content-type", "")
    res["markdown"] = {"status": st, "content_type": ct, "serves_markdown": "markdown" in ct.lower(),
                       "vary": hd.get("vary"), "cache_control": hd.get("cache-control")}
    return res


def own_issues(o):
    out = []
    h, r = o["html"], o["robots"]
    if o["page"]["status"] != 200: out.append(f"page status {o['page']['status']}")
    if h["jsonld_blocks"] == 0: out.append("no JSON-LD blocks")
    if h["jsonld_parse_errors"]: out.append(f"{h['jsonld_parse_errors']} JSON-LD block(s) fail to parse")
    if h["h1_count"] != 1: out.append(f"h1 count is {h['h1_count']} (want 1)")
    if not h["canonical"]: out.append("missing canonical")
    if not h["meta_description"]: out.append("missing meta description")
    if not h["meta_author"]: out.append("missing meta author")
    if h["hidden_text_hits"]: out.append(f"{h['hidden_text_hits']} hidden-text hit(s) in SSR HTML, e.g. {h['hidden_text_samples'][:2]}")
    if h["images_missing_alt"]: out.append(f"{h['images_missing_alt']} image(s) without alt attribute")
    if r["status"] != 200: out.append(f"robots.txt status {r['status']}")
    for b, s in r["bots"].items():
        if s == "BLOCKED": out.append(f"{b} is blocked in robots.txt")
    if r.get("cf_cache_status") in ("HIT", "STALE") and r.get("age"):
        out.append(f"robots.txt served from CDN cache (age {r['age']}s): purge after edits")
    for path, w in o["well_known"].items():
        if w["status"] != 200: out.append(f"{path} -> {w['status']}")
    if not o["markdown"]["serves_markdown"]: out.append("Accept: text/markdown not served as markdown")
    return out


# ---------- report ----------
def load_baseline(path):
    d = json.load(open(path))
    g = d.get("geo") or d
    return {"score": g.get("score"), "bd": g.get("score_breakdown") or {},
            "lh": (d.get("lighthouse") or {}).get("seo")}


def build_md(rep, base):
    g, lh = rep["geo"], rep["lighthouse"]
    bd = g.get("score_breakdown") or {}
    L = [f"# AEO/SEO report: {rep['url']}", "", f"- Time: {rep['timestamp']}"]
    if "score" in g:
        d = f" ({g['score'] - base['score']:+d} vs baseline)" if base and base["score"] is not None else ""
        L.append(f"- GEO score: **{g['score']}/100** ({g.get('band')}){d}")
    else:
        L.append(f"- GEO score: unavailable ({g.get('error')})")
    if lh and "seo" in lh:
        d = f" ({lh['seo'] - base['lh']:+d})" if base and base.get("lh") is not None else ""
        L.append(f"- Lighthouse SEO: **{lh['seo']}**{d}")
    L += ["", "## Points by category", "", "| Category | Points | Max | Gap | Delta |", "|---|---|---|---|---|"]
    gaps = []
    for c, mx in CATS.items():
        pts = bd.get(c)
        if pts is None: continue
        gap = mx - pts; gaps.append((gap, c))
        dl = f"{pts - base['bd'][c]:+d}" if base and c in base["bd"] else ""
        L.append(f"| {c} | {pts} | {mx} | {gap} | {dl} |")
    if "negative_penalty" in bd: L.append(f"| negative_penalty | {bd['negative_penalty']} | 0 | | |")
    L += ["", "## Gaps by recoverable points", ""]
    for gap, c in sorted(gaps, reverse=True):
        if gap > 0: L.append(f"- {c}: {gap} pt")
    L += ["", "## geo-optimizer recommendations", ""] + [f"- {r}" for r in (g.get("recommendations") or [])]
    if lh and lh.get("failed"):
        L += ["", "## Lighthouse SEO failed audits", ""] + [f"- {a['id']}: {a['title']}" for a in lh["failed"]]
    o = rep["own"]
    L += ["", "## Own checks", "", "Issues:"] + [f"- {i}" for i in rep["own_issues"]] or ["- none"]
    L += ["", f"- JSON-LD types: {', '.join(o['html']['jsonld_types']) or 'none'}",
          f"- robots.txt: status {o['robots']['status']}, cf-cache {o['robots'].get('cf_cache_status')}, age {o['robots'].get('age')}",
          "", "| AI bot | robots.txt |", "|---|---|"] + [f"| {b} | {s} |" for b, s in o["robots"]["bots"].items()]
    L += ["", "| File | Status | Content-Type |", "|---|---|---|"] + \
         [f"| {p} | {w['status']} | {w['content_type'] or ''} |" for p, w in o["well_known"].items()]
    L.append(f"\n- Accept: text/markdown -> {o['markdown']['content_type']} (vary: {o['markdown']['vary']})")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser(description="SEO + AEO/GEO scorer", formatter_class=argparse.RawDescriptionHelpFormatter,
                                 epilog="See the USAGE docstring at the top of this file.")
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", default="aeo-report")
    ap.add_argument("--baseline")
    ap.add_argument("--no-lighthouse", action="store_true")
    ap.add_argument("--allow-local", action="store_true", help="allow localhost/loopback targets")
    a = ap.parse_args()
    url = a.url if re.match(r"(?i)^https?://", a.url) else "https://" + a.url
    host = urlparse(url).hostname or ""
    if host in LOCAL_HOSTS and not a.allow_local:
        sys.exit("localhost target: pass --allow-local (loopback only; host-gated checks differ).")
    if a.allow_local and host not in LOCAL_HOSTS:
        sys.exit("--allow-local only accepts localhost, 127.0.0.1 or ::1.")
    os.makedirs(a.out, exist_ok=True)
    from datetime import datetime, timezone
    print("geo audit ...", file=sys.stderr); g = geo_audit(url, a.allow_local)
    lh = None
    if not a.no_lighthouse: print("lighthouse ...", file=sys.stderr); lh = lighthouse(url)
    print("own checks ...", file=sys.stderr); o = own_checks(url)
    rep = {"url": url, "timestamp": datetime.now(timezone.utc).isoformat(), "geo": g, "lighthouse": lh,
           "own": o, "own_issues": own_issues(o)}
    base = load_baseline(a.baseline) if a.baseline else None
    json.dump(rep, open(os.path.join(a.out, "report.json"), "w"), indent=2)
    md = build_md(rep, base)
    open(os.path.join(a.out, "report.md"), "w").write(md)
    bd = g.get("score_breakdown") or {}
    print(f"URL: {url}")
    if "score" in g:
        s = f"GEO {g['score']}/100 ({g.get('band')})"
        if base and base["score"] is not None: s += f"  delta {g['score'] - base['score']:+d} (baseline {base['score']})"
        print(s)
        if base:
            ch = [f"{c} {bd[c] - base['bd'][c]:+d}" for c in CATS if c in bd and c in base["bd"] and bd[c] != base["bd"][c]]
            print("Category deltas: " + (", ".join(ch) or "none"))
    else:
        print("GEO unavailable:", g.get("error"))
    if lh and "seo" in lh:
        s = f"Lighthouse SEO {lh['seo']}"
        if base and base.get("lh") is not None: s += f"  delta {lh['seo'] - base['lh']:+d}"
        print(s)
    gaps = sorted(((CATS[c] - bd[c], c) for c in CATS if c in bd and CATS[c] > bd[c]), reverse=True)
    print("Top gaps: " + (", ".join(f"{c} -{n}" for n, c in gaps[:4]) or "none"))
    print(f"Own issues: {len(rep['own_issues'])}")
    for i in rep["own_issues"][:6]: print("  -", i)
    print(f"Wrote {a.out}/report.json and report.md")


if __name__ == "__main__":
    main()
