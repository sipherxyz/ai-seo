# Security Policy

## Reporting a vulnerability

Please do not report security problems in public issues, pull requests, or discussions.

Report them privately through GitHub:
**Security** tab > **Report a vulnerability**
(https://github.com/sipherxyz/ai-seo/security/advisories/new).

Include:
- what is affected (file, script, option),
- steps to reproduce,
- the impact you expect.

We aim to reply within 5 business days and to keep you updated until the issue is fixed.

## Supported versions

Only the latest commit on `main` is supported.

## Scope notes

`scripts/score.py` fetches the URL you give it and runs `uvx` and `npx` tools.
Run it only against sites you are allowed to test. The `--allow-local` option un-blocks loopback addresses only.
