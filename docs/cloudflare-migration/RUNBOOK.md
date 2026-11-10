# Raven Crow — Cloudflare runbook

Operator: Claude Code (hosting). Escalation: Guilherme (account owner: Cloudflare, GitHub, Buffer). Editorial content and the cut pipeline (`D:\CorteFlow`, n8n, daemon, ReservaGPT, Buffer) are **not** operated from here.

## Architecture (2026-11-07)

```
GitHub main (TrueBinary/raven-crow-biblioteca)
   │  pipeline pushes clips; editors/builders push pages
   ▼
release.mjs  ── integrity gate (content-integrity + public-pages) ── delete-free sync ──▶ R2 bucket raven-crow-media
   ▲  runs: GitHub Actions "Publicar site" (site-release.yml) on every push to main, hourly at :17 and by hand — since 2026-11-10:
   │        1) imports link photos, runs the 4 builders, commits generated pages as github-actions[bot] and pushes
   │           them to main if both validators pass; 2) releases main to R2
   │        The Windows task "Raven Crow - release site R2" (release-local.ps1) is disabled; it is the rollback.
Worker raven-crow-site-production  ◀── routes ravencrow.cloud/*, www.ravencrow.cloud/* (DNS AAAA 100:: proxied)
   └─ serves R2; GITHUB_FALLBACK=1 serves GitHub Raw for keys not yet released (header x-raven-migration-stage)
```

## Daily / on demand

| Check | Command | Healthy |
| --- | --- | --- |
| Full health | from `D:\CorteFlow\work\raven-cf-release`: `node <handoff>/ops/cloudflare/health-check.mjs` (set `CLOUDFLARE_ACCOUNT_ID` for the R2 inventory) | exit 0, `problems: []` |
| Domain only | `node ops/cloudflare/verify-domain.mjs https://ravencrow.cloud/ https://www.ravencrow.cloud/` | both `ok: true` |
| Release log | GitHub → Actions → Publicar site → last run → summary | `healthChecksPassed: true` |
| Last released commit | `deployedSha` in the last run summary | equals `git rev-parse origin/main` |
| Clip ready for Buffer | `node ops/cloudflare/video-url.mjs <url> <sha256> <bytes>` | exit 0 |
| Integrity of a commit | `node ops/cloudflare/content-integrity.mjs <sha>` / `public-pages.mjs <sha>` | `errors: []` |

The health check covers: apex + www (no Render, TLS, Worker marker), feed JSON with ≥ 12 articles, every sitemap page (no 5xx, warns on `github-fallback`), 3 sampled clips (HEAD + Range), and R2 vs Git for the last released commit (missing / different objects).

## Incidents

**Apex or www 503 / `x-render-routing`** — DNS was pointed back at Render. Restore `AAAA 100::` proxied for the host (see OPERATIONS-LEDGER) and re-run the domain check.

**Release log `PAGES FAILED` / `PAGES BLOCKED`** — a builder crashed or the generated pages fail a validator; nothing was pushed. Read the lines below it in the log.

**Release log `FAILED` or `RELEASE BLOCKED`** — read the reason line:
- `content validation failed` → an editorial file is broken (invalid JSON, missing page, sitemap URL without page, canonical/CSS/ads/PostHog). Nothing was published; fix the content in Git. The site keeps serving the previous release.
- `R2 sync failed ... existing object differs` → a media key (clip/photo) was reused with new bytes. Never overwrite: rename the file (new hash) in Git.
- `health check failed` → the sync finished but the site is unhealthy; run the full health check.
- `401` from Cloudflare → the `cf` CLI login expired: run `cf auth login` once.
- `fetch failed` → transient network; the next run retries automatically (the SHA is only marked released on success).

**Clip 404 for Buffer** — check the release log; dispatch Publicar site by hand (Actions → Run workflow). With `GITHUB_FALLBACK=1` a pushed clip plays immediately from GitHub.

## Rollback

| What | How | Note |
| --- | --- | --- |
| Worker code | Cloudflare API `POST /accounts/<acct>/workers/scripts/raven-crow-site-production/deployments` `{"strategy":"percentage","versions":[{"version_id":"<previous>","percentage":100}]}` | versions: `41b1e7ca` (current) → `ae91889c` → `62ee25cc` → `38f7a94a` → `48656803` → `2dd11af1` → `fc40f4a6` → `b9785878`; all still listed |
| DNS | restore the records in OPERATIONS-LEDGER | Render is suspended: returning to it brings the 503 back |
| Content | revert the commit in Git; the next release re-syncs text files | media is never deleted, old objects stay in R2 |
| Release automation | disable the Windows task "Raven Crow - release site R2" | the site keeps serving the last release |

Never: delete R2 objects or Git media, force-push, point DNS at Render, or change n8n/daemon/Buffer schedules from here.

## Turning off the GitHub fallback (final step of the migration)

Only after both: (1) GitHub Actions is unlocked or the Windows task is proven over several days, and (2) the pipeline waits for R2 before scheduling (see `ops/cloudflare/video-handoff-contract.md`). Then redeploy the Worker without `GITHUB_FALLBACK` and run the health check: no page or clip may show `github-fallback`.

## Open items (2026-11-07)

- GitHub account locked for billing: `news-pages.yml` (page builder) and the release workflow do not run. Effects: 5 newest articles lack analytics/schema/sitemap entries; the Windows task replaces only the release.
- PR TrueBinary/raven-crow-biblioteca#1 not merged (front-page photo fix, tools, workflow).
- Cloudflare error-log alerting is not wired (needs an analytics token); the health check covers HTTP symptoms only.
