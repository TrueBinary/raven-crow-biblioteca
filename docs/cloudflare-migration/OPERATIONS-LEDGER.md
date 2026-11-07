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
