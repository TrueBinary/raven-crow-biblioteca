# Raven Crow — deploy via Cloudflare Workers Builds (design)

Date: 2026-11-07. Status: proposed.

## Why

GitHub Actions on TrueBinary is locked for billing. `news-pages.yml` (4 Python builders that commit generated pages, covers and photos) no longer runs, so every news commit arrives without its generated files and the release gate correctly blocks publication. Today a person (or agent) has to run the builders and push by hand. Render used to build on push on its own infrastructure; we want the same on Cloudflare, without GitHub Actions and without depending on the user's PC.

## Decision

Connect the repo `TrueBinary/raven-crow-biblioteca` (branch `main`) to the existing Worker `raven-crow-site-production` with **Workers Builds**. On each push:

1. **Build command** `node ops/cloudflare/build-and-release.mjs`:
   1. hydrate generated photos and their credits from R2 (R2 is the store of what is already published), so the photo builder only searches Commons for articles that have no published photo;
   2. run `build-raven.py`, `build-column.py`, `build-news-index.py`, `build-library.py`;
   3. validate the built working tree with `content-integrity` and `public-pages` (errors abort: nothing is uploaded);
   4. phased, delete-free sync of the built tree (`index.html` + `public/**`) to R2;
   5. health check (apex, www, feed).
2. **Deploy command** `npx wrangler deploy` with a committed `wrangler.jsonc` describing the current Worker (same name, code, R2 binding, `GITHUB_FALLBACK=1`, routes). It runs only when the build command succeeded.

Generated files no longer need to be committed. Editors only commit source data (`public/noticias.json`, `public/coluna-ensaios.json`, `index.html`, etc.).

## Goals

- A news commit is live within one build (~minutes) with its page, cover, sitemap entry and analytics, with no manual step.
- Same safety as today: validation before any write; media never overwritten or deleted; phased upload; failed build leaves the site on the last good state.
- No dependency on GitHub Actions or the user's PC.

## Non-goals

- Changing the cut pipeline, n8n, Buffer, ReservaGPT or editorial agents.
- Moving clips out of Git or changing `/clips/<sha>.mp4` URLs.
- Turning off `GITHUB_FALLBACK` (separate step; see `ops/cloudflare/video-handoff-contract.md`).

## Anti-goals

- A photo credit that does not match the published photo (attribution error).
- Overwriting an already-published photo or clip with different bytes.
- A build that publishes partial content after a failure.

## Constraints

- Workers Builds free plan: 3,000 build minutes/month, 20 min timeout, 20 GB disk, 1 concurrent build; Node 24 and Python 3.14 preinstalled. Builders use only the Python standard library.
- Clip-only commits (~16/day) must not trigger builds: build watch paths exclude `public/clips/*`. New clips reach R2 on the next build; until then the fallback serves them.
- R2 access from the build uses a scoped API token stored as build secret `R2_API_TOKEN` (Workers R2 Storage: Edit) and build variable `CLOUDFLARE_ACCOUNT_ID`. Never in Git or logs.
- Connecting the repo, watch paths and build secrets are dashboard steps the account owner does.

## Left to the builder

File layout inside `ops/cloudflare/`, exact log format, wrangler version pin (exact version, ≥ 2 weeks old).

## Unverified

Whether the Cloudflare GitHub app receives push webhooks while the GitHub account is billing-locked; clone time for the 2.4 GB repo. Both are measured in the first build (Task 6); if webhooks do not arrive, keep the Windows task.
