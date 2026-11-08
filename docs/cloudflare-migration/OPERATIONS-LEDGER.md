# Raven Crow — Cloudflare operations ledger

No secrets here: endpoints, record types, IDs and check results only.

## 2026-11-07 — P0 apex 503 fixed (Task 1)

**Cause:** Worker routes `ravencrow.cloud/*` and `www.ravencrow.cloud/*` (script `raven-crow-site-production`) already existed, but the apex DNS record was `A 216.24.57.1` (Render edge, itself on Cloudflare for SaaS). Render answered first with `503 x-render-routing: suspend-by-user`. `www` (CNAME to `raven-crow-biblioteca.onrender.com`) worked only by chance.

**Change (zone `ravencrow.cloud`, id `e1d1e720223512ed47da095648798f70`):**

| Item | Before | After |
| --- | --- | --- |
| DNS `ravencrow.cloud` (id `f46183c1856c59e8f98c68a509ed6d77`) | A `216.24.57.1` proxied | AAAA `100::` proxied (originless, Worker-only) |
| DNS `www.ravencrow.cloud` | CNAME `raven-crow-biblioteca.onrender.com` proxied | AAAA `100::` proxied |
| Zone setting `always_use_https` | off (Render did the redirect) | on |
| Worker routes | apex + www -> `raven-crow-site-production` | unchanged |
| TXT google-site-verification | present | unchanged |

**Evidence (2026-11-07 ~15:01 BRT):** `https://ravencrow.cloud/` and `https://www.ravencrow.cloud/` 200 with `X-Raven-Migration-Stage: r2`, no `x-render-routing`; `http://ravencrow.cloud/` 301 -> https; TLS verify 0; `/editorial-feed.json` valid JSON with 12 items on both hosts; `/sitemap.xml` 200. `node --test tests/cloudflare/verify-domain.test.mjs` -> 9/9 (live checks included).

**Rollback (Cloudflare API, zone above):**
- apex: `PUT /dns_records/f46183c1856c59e8f98c68a509ed6d77` `{"type":"A","name":"ravencrow.cloud","content":"216.24.57.1","proxied":true}` — note Render is suspended, so this brings the 503 back.
- www: `PUT` the www record back to `CNAME raven-crow-biblioteca.onrender.com` proxied.
- https: `PATCH /settings/always_use_https {"value":"off"}`.

**Still open:** R2 holds only part of the site (no MP4s); the Worker still falls back to GitHub Raw for missing keys (Tasks 2–4).

## 2026-11-07 — Worker deploy (Task 4)

- Before: version `b9785878-fb3d-4fb6-91b0-727aa6fc9df8` (identical to repo `raven-production-worker.mjs` at 9ba11ca; fallback always on).
- After: version `fc40f4a6-3994-4b6f-8acd-9957155edaea` from commit 1dac515. Bindings: `RAVEN_MEDIA` -> `raven-crow-media`, `GITHUB_FALLBACK=1` (plain text).
- Why the flag stays on: approved clips land in GitHub main before reaching R2; until the main->R2 release is automatic (Task 6) the fallback keeps new clips playable. Set `GITHUB_FALLBACK` to anything else (or remove it) to serve R2 only.
- Evidence: apex/www probe 9/9; `/`, `/noticias.html`, `/sitemap.xml`, `/editorial-feed.json`, `/raven-frontpage.js`, newest clip all 200 `r2`; clip Range 206; `/__migration/import` 404.
- Rollback: `POST /accounts/<account>/workers/scripts/raven-crow-site-production/deployments` with `{"strategy":"percentage","versions":[{"version_id":"b9785878-fb3d-4fb6-91b0-727aa6fc9df8","percentage":100}]}`.

## 2026-11-07 — Worker deploy (Task 8)

- Version `2dd11af1-4d81-4ef6-a164-fffb1c1c037a` from commit e9e3085: hash-named clips (`clips/<sha256>.mp4|jpg`) served with `Cache-Control: public, max-age=31536000, immutable`; HTML/JSON/XML 60 s; other assets 300 s. Bindings unchanged (`RAVEN_MEDIA`, `GITHUB_FALLBACK=1`).
- Evidence: probe 9/9; `/` and feed 60 s; clip mp4/jpg immutable, served from `r2`; Range 206 on www.
- Rollback: deployments API to version `fc40f4a6-3994-4b6f-8acd-9957155edaea`.

## 2026-11-08 — Worker deploy (social bar)

- Version `48656803-7585-49f1-87be-a7d6c104d812` from commit a4ad38e (includes d967ce9): social bar script appended before `</body>` on every 200 HTML response. Bindings unchanged.
- Evidence: `/`, `/noticias.html` and an article page carry the script once; JS/health untouched.
- Rollback: deployments API to version `2dd11af1-4d81-4ef6-a164-fffb1c1c037a`.

## 2026-11-08 — Worker deploy (GTranslate)

- Version `38f7a94a-a704-4d18-b62b-d3a730f24cb4` from commit ae54001: GTranslate float switcher (pt default; en, es, fr, de, it; bottom-left) after the social bar, before `</body>`.
- Rollback: deployments API to version `48656803-7585-49f1-87be-a7d6c104d812`.

## 2026-11-08 — Worker deploy (en/es editions)

- Version `62ee25cc-a3ae-4d11-b5c6-ba189b47b9d4` from commit 459d0f5: `/en`, `/es` and `/<lang>/noticias/<id>` without trailing slash map to their index.html.
- Rollback: deployments API to version `38f7a94a-a704-4d18-b62b-d3a730f24cb4`.

## 2026-11-08 — Worker deploy (favicon)

- Version `ae91889c-b7b7-4afb-84e8-3e0e2595997b` from commit e1adee1: same favicon links (favicon.ico, raven-logo.webp, apple-touch-icon) in `<head>` of every HTML page lacking one.
- Rollback: deployments API to version `62ee25cc-a3ae-4d11-b5c6-ba189b47b9d4`.

## 2026-11-08 20:06 — Worker 41b1e7ca: favicon em alta resolução
- Ícones gerados do logo "Corvo no machado" (favicon.ico 16/32/48, icon-192, icon-512, apple-touch-icon 180) — site main b76d40b.
- Worker ICONS aponta para os PNGs (fbcc84f); deploy 100% em 41b1e7ca com OK do usuário. Rollback: ae91889c.
- Release das 20:02 travou: favicon.ico era tratado como mídia imutável no R2 (r2 9608 B ≠ git 5569 B). Fix 0c08093: `isMutable('favicon.ico')` = true; clips/fotos continuam imutáveis.
