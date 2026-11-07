# Raven Crow — Cloudflare Operations Handoff Implementation Plan

> **For agentic workers (Claude Code):** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended, because DNS and publishing failures are high-impact) or superpowers:executing-plans. Execute the plan task-by-task. Each task uses RED -> GREEN -> verification -> small commit. Do not claim success without fresh evidence.

**Goal:** Claude Code must assume the Raven Crow site's Cloudflare hosting, complete the migration of the media library, fix the apex-domain outage, and maintain automatic safe publishing without changing or breaking the local editorial and video machinery.

**Architecture:** GitHub (source of truth) -> existing Python site builders -> validated artifacts -> Cloudflare Worker `raven-crow-site-production` backed by private R2 bucket `raven-crow-media`. Keep the existing temporary GitHub Raw fallback for unimported files until all objects and new-write paths are verified, then retire it. Local agents, n8n, daemon, ReservaGPT and Buffer remain independent producers/consumers.

**Tech Stack:** Python 3.12, Node.js, GitHub Actions, Cloudflare Workers, R2, Cloudflare DNS/TLS, Git, current Raven Crow static HTML/CSS/JS. Follow existing Cloudflare project conventions; no Wrangler config is present in the main repository as audited; prefer the official `cf` CLI per Cloudflare guidance if available, and use official authenticated API otherwise. Do not install a competing deployment tool by default.

**Spec:** `docs/superpowers/specs/2026-11-07-raven-crow-cloudflare-operations.md` (read it first). Background, partially stale: `docs/cloudflare-migration/PLAN-2026-11-07.md`. Existing contracts: `AGENTS.md`, `EDITORIAL.md`.

## Message to Claude Code — read this first

You are the maintainer taking over **Raven Crow hosting and distribution on Cloudflare**, NOT replacing its editorial staff or rebuilding its productive local pipeline. Treat everything as running infrastructure, not a greenfield project. Read this complete file, the spec and AGENTS.md. Work in a new worktree and on a fresh branch from current `origin/main`. Keep a progress ledger and enumerate what you verified. Make a reversible checkpoint before every environment change. Do not blindly revert agents' commits. Always fix the site outage first and never expose credentials, overwrite old media, force-push or edit live n8n/daemon/Buffer configurations in this plan. When a change can affect the public site, stage, test and report before releasing.

## State recorded on 2026-11-07 (re-verify before work)

| Component | Observed state | Meaning for Claude |
| --- | --- | --- |
| Cloudflare zone | `ravencrow.cloud` **active**, NS `ace.ns.cloudflare.com` / `sandy.ns.cloudflare.com` | Delegation completed; this alone is not a successful site cutover |
| HTTPS apex | `https://ravencrow.cloud/` returned **503**; response included `x-render-routing: suspend-by-user` | **P0 BUG**: traffic still fell through to suspended Render despite Cloudflare proxy |
| HTTPS www | `https://www.ravencrow.cloud/` returned **200** and `X-Raven-Migration-Stage: r2` | Working reference for diagnosis |
| Workers | `raven-crow-site-production`; routes `ravencrow.cloud/*` and `www.ravencrow.cloud/*` | DO NOT replace blindly; debug apex route or migrate safely to Worker Custom Domains |
| R2 | Private bucket `raven-crow-media`, binding `RAVEN_MEDIA`; **78 objects totaling 395,317 bytes, 0 MP4s** | Most static files and **all videos** still missing |
| R2 inventory trap | Object listing requires `per_page=1000` and/or cursor. `limit=1000` was ignored and returned only 20 | Always paginate; write a regression test |
| GitHub site | `TrueBinary/raven-crow-biblioteca`; source root `index.html` and `public/**` | Tracked GitHub main is source of truth, not the stale Windows checkout |
| Repository audit | 351 tracked site files, about 2.37 GB, 65 MP4s (~2.27 GB) in Git at last inventory | Recount and reconcile with SHA256 before any upload |
| News | `public/editorial-feed.json` and `public/noticias.json` repaired; one missing CMO page restored; feed had 12 items | Check current JSON and actual links; editorial checks still required |
| Local Git checkout | `D:\CorteFlow\work\raven-crow-biblioteca` was dirty and ahead/behind remote main | NEVER checkout/reset/rebase that shared worktree |
| Render | `raven-crow-biblioteca` suspended by billing | Do not assume fallback to Render works |
| Migration code | Branch `cloudflare-migration-staging-20261107` contains `ops/cloudflare/raven-production-worker.mjs` and `ops/cloudflare/raven-r2-worker.mjs` | Review this code, do not confuse the test import Worker with the production Worker |
| Operational core | n8n, daemon, ReservaGPT and Buffer run outside this website migration | Preserve unchanged; any later transport integration is a separate release |

## Global Constraints

1. **Non-negotiable:** Never change n8n workflows, the daemon/cutter, ReservaGPT automation prompts, Buffer queues, video IDs or scheduling logic as part of hosting migration.
2. Never point the domain to suspended Render; no API or billing assumptions. Preserve DNS TXT, MX, DKIM, SPF, DMARC, CAA, subdomains, redirects and DNSSEC as actually found.
3. Never delete GitHub or R2 media during migration. Do not change public MP4 paths `/clips/<sha>.mp4`, news URLs or SEO canonicals.
4. Keep the Raven Crow visual identity (dark/black, red/coral, white, logo), responsive layout, ad disclosures, relevant images, news, opinions and book pages intact.
5. Factual news must have traceable trustworthy sources and article date; do not generate or repeat unsupported political allegations. Do not use synthetic stories to fill missing content.
6. Never publish secrets to Git, R2 web paths, CI logs or client JS. Least-privilege scoped credentials in secret stores, never write them to disk/commit.
7. Work from fresh `origin/main` in a clean independent worktree; use small PRs with focused scopes and ordinary fast-forward/review; no `git reset --hard`, `git clean -fdx` on others' folders, no force-push.
8. Red-green TDD and full repo test command from AGENTS.md for each significant behavior change. Diagnose existing failures rather than hiding or deleting tests.
9. No public upload/import endpoint. The reference **staging** Worker has an importer endpoint requiring a secret, but production Worker must reject `/__migration/*`. Prefer authorized server-to-R2 transfer through CLI or scoped credentials; remove old staging importer after completion.
10. Preserve compatibility with queued and previously published Instagram, YouTube and Buffer media URLs; reconcile ledger/hash before editing a transport adapter.
11. Do not imply "fully on Cloudflare" while any file still uses GitHub Raw fallback. Document remaining objects and feature flags quantitatively.
12. If a release fails a gate, stop the cutover, preserve healthy service, produce rollback instructions and report blocker with evidence instead of improvising.

## Review Focus — input classes to test

- **DNS/hostname mismatch:** Cloudflare active but apex gets Render 503 while www serves Worker 200 -> explicit apex regression in Task 1.
- **Partial object listing:** >20 R2 objects with cursor pagination -> no silent undercount, Task 2.
- **Byte ranges:** HEAD, GET, suffix/single-byte, unsatisfiable and malformed Range; correct 200/206/416, Content-Range and lengths, Task 4.
- **Concurrent publishing:** generator commits while deployment reads assets -> same Git SHA for manifest, outputs and R2 sync, Task 6.
- **Untrusted editorial data:** malformed JSON, absent news HTML, missing image, duplicate article ID or unverified source -> reject/repair deterministically without inventing facts, Task 7.

## Repository map / ownership contract

| Area | Files or service | Responsible agent |
| --- | --- | --- |
| Website source | `index.html`, `public/**`, site CSS/JS | Editorial/website builders; Claude deploys validated outputs |
| Content builders | `build-raven.py`, `build-news-index.py`, `build-column.py`, `build-library.py`, `raven_seo.py` | Existing site pipeline, Claude can maintain with tests |
| Editorial stores | `public/noticias.json`, `public/editorial-feed.json`, `public/coluna-ensaios.json` and archives | Editorial agents; Claude may reconcile publication, not invent new items |
| Existing GH workflow | `.github/workflows/news-pages.yml` | Builder that can commit outputs to main; coordinate; do not delete |
| Cloudflare sources | `ops/cloudflare/raven-production-worker.mjs` (migration branch), `raven-r2-worker.mjs` | Claude maintains and tests; only stable production script can route live |
| New proposed sync tools | `ops/cloudflare/inventory.mjs`, `ops/cloudflare/r2-sync.mjs`, `ops/cloudflare/verify-domain.mjs` | Claude creates in clean worktree with tests |
| New CI | `.github/workflows/cloudflare-site-release.yml` | Claude creates separate job, avoiding recursive triggers |
| New unit tests | `tests/cloudflare/*.test.mjs` | Claude owns |
| Migration runbooks | `docs/cloudflare-migration/` and `docs/superpowers/` | Claude owns |
| Video production | `D:\CorteFlow` and `D:\ReservaGPT` plus separate n8n/daemon | **Out of scope; read-only audit only** |
| Media publishing | Buffer and current public video URLs | **Out of scope until a separately tested handoff** |

## Preflight: before Task 1

- [ ] Read `AGENTS.md`, `EDITORIAL.md`, this spec and this plan, existing Cloudflare Worker sources and `.github/workflows/news-pages.yml`.
- [ ] Fetch `origin/main`, create a new clean worktree and branch (e.g. `cf-handoff-p0-20261107`). NEVER use the dirty shared Windows checkout as working tree.
- [ ] Record branch SHA, R2 inventory count (using `per_page` and cursor), Cloudflare routes, DNS records, zone/SSL status, GH workflow state and current production headers in `docs/cloudflare-migration/OPERATIONS-LEDGER.md`.
- [ ] Run existing baseline: `python -m unittest discover -s tests -q` and JS checks from AGENTS.md. Record any preexisting failures before editing.
- [ ] No secrets in this ledger. Name endpoints, service names, check results and commit SHAs only.

---

### Task 1 — P0: eliminate the apex-domain 503

**Files:** Create `ops/cloudflare/verify-domain.mjs`, `tests/cloudflare/verify-domain.test.mjs`. Update only Cloudflare route/DNS/custom domain configuration after comparing a fresh snapshot.

**Interfaces:**
- Produces `verifyHost(url: string, opts?: { expectedMarker?: string }): Promise<{ status: number; cfRay: boolean; stage: string | null; renderSuspend: boolean; tlsOk: boolean }>`.
- Consumed by Tasks 4, 6 and 9.

- [ ] **RED:** Test detects failing apex: HTTP 503 or `x-render-routing` must fail, even if DNS answers Cloudflare IP; successful `www` 200 is not enough. Test no redirect loop and valid TLS.
- [ ] **Verify RED:** run `node --test tests/cloudflare/verify-domain.test.mjs`; the apex case must fail against current production symptom, not because of a missing module or unauthorized call.
- [ ] **Investigate:** compare DNS apex and www, Worker routes, route pattern matching, zone status, SSL certificate, Cloudflare event/request traces and origin fallthrough. Prefer **Workers Custom Domain** for an originless site (per Cloudflare docs) only after validating that removing conflicting records won't break others; snapshot previous records/routes.
- [ ] **GREEN:** make the minimal Cloudflare configuration change, without changing other software. Confirm apex and www hit the intended Worker, no `x-render-routing`, and expected response header `X-Raven-Migration-Stage`.
- [ ] **Verify:** `node --test tests/cloudflare/verify-domain.test.mjs`; `curl -sSI https://ravencrow.cloud/` and `curl -sSI https://www.ravencrow.cloud/` both 200 with HTTPS valid, no Render header; both `/editorial-feed.json` valid JSON. Test HTTP->HTTPS and canonical policy.
- [ ] **Checkpoint:** save anonymous DNS/route state and rollback commands, small commit `fix(cloudflare): route apex hostname to Worker`. Only mark P0 complete with external HTTP evidence.

### Task 2 — inventory and complete migration manifest

**Files:** Create `ops/cloudflare/inventory.mjs` and `tests/cloudflare/inventory.test.mjs`; generated report `docs/cloudflare-migration/media-manifest-summary.json` (NO secrets or private metadata).

**Interfaces:**
- Produces `getSourceManifest(gitRef: string): Promise<Array<{ key: string; size: number; sha256: string; mime: string }>>`, using Git tree + checked-out content.
- Produces `listR2All(): Promise<Array<{ key: string; size: number; etag?: string }>>`; handle `per_page=1000`, `result_info.is_truncated` and `cursor`. Do **not** assume ETag equals SHA256.
- Produces `diffManifests(source, destination): { missing: string[]; different: string[]; matching: string[] }` for Task 3.

- [ ] **RED:** Test 2-page pagination with 20-object first page; same key/different byte count, collision, missing source and key safety; a mock returning exactly 20 but `is_truncated=true` must NOT be treated as complete.
- [ ] **Verify RED:** `node --test tests/cloudflare/inventory.test.mjs`.
- [ ] **Implement:** inventory `index.html` at repository root as R2 key `index.html`; inventory published `public/**` keys without the prefix `public/`; exclude local secrets, `.git`, caches and untracked content. Confirm origin Git commit SHA and total bytes.
- [ ] **GREEN:** both the tests and a read-only dry-run inventory pass. Confirm baseline ~351 files, ~65 MP4s against current Git (may have changed); R2 baseline 78 objects, zero MP4s as of audit.
- [ ] **Commit:** `feat(cloudflare): deterministic media inventory and paginated R2 reconciliation`.

### Task 3 — transfer all media and site assets to private R2 safely

**Files:** Create `ops/cloudflare/r2-sync.mjs`, `tests/cloudflare/r2-sync.test.mjs` and a resumable state manifest stored outside the public web root; optional `ops/cloudflare/r2-sync.config.json` with NONSECRET settings only.

**Interfaces:**
- Consumes Task 2 manifest/diff.
- Produces `syncMedia({ gitRef, dryRun, maxConcurrency, resume }): Promise<{ uploaded: number; skipped: number; verified: number; failed: Array<{key:string; reason:string}> }>`.

- [ ] **RED:** Unit cases: already uploaded object is skipped; same key/different checksum stops; failed part retries without duplicate complete; interrupted upload resumes; cannot upload paths outside whitelist; no delete; 65 MP4s preserved at exact hash-named keys.
- [ ] **Verify RED:** `node --test tests/cloudflare/r2-sync.test.mjs` must fail for missing behavior.
- [ ] **Implement:** use authorized Cloudflare S3-compatible R2 credentials (scoped to `raven-crow-media`) or official authenticated `cf` CLI; **do not** hardcode tokens, do not create a public import endpoint, and never print credentials. Streaming/multipart for large MP4s; small images/assets too. Verify bytes + SHA256 end-to-end, not only HTTP 200.
- [ ] **Dry run:** inspect planned copies, sizes and total transfer before writing. Upload first a small text file, one JPG/PNG and one large MP4; verify read and range.
- [ ] **Full transfer:** upload remaining objects with resume/checkpoint and throttled concurrency; do not delete originals; cross-check Git SHA + object counts. Explicitly reconcile every `/clips/<sha>.mp4` used by Buffer, using approved local ledgers in read-only mode.
- [ ] **Verify:** `node --test tests/cloudflare/r2-sync.test.mjs`; zero missing or different objects; at least the full media count present; run external GET/HEAD/Range checks for sampled MP4s including largest. Record verified manifest and timestamp.
- [ ] **Commit:** `feat(cloudflare): idempotent authenticated R2 media sync`.

### Task 4 — Worker correctness and removal of GitHub dependency

**Files:** Modify `ops/cloudflare/raven-production-worker.mjs` in branch; add `tests/cloudflare/worker.test.mjs`. Verify deployed script matches the reviewed SHA. **Never** deploy staging importer to production.

**Interfaces:**
- Consumes R2 data from Task 3 and `verifyHost` from Task 1.
- Produces Worker route handling for `GET`, `HEAD` and standard cached response/conditional request semantics.

- [ ] **RED:** Tests for root `/`, static pages, trailing-slash article paths, image and JS MIME, rejects `..` and encoded traversal, 404 for absent resources, 405 for disallowed methods, 404 for `/__migration/*`.
- [ ] **RED:** MP4 tests for `Range: bytes=0-15` (206 + exact 16 bytes), suffix range, unsatisfiable range (416 + `Content-Range: bytes */size`), HEAD 200 with full Content-Length and no body, GET 200, ETag/304.
- [ ] **Verify RED:** `node --test tests/cloudflare/worker.test.mjs`.
- [ ] **Implement:** use R2 binding `RAVEN_MEDIA` as the definitive origin. For all objects confirmed in Task 3, no network fetch from GitHub. Keep fallback **feature-gated** temporarily until coverage is full; it must be disabled in the final production release. Ensure metadata, content lengths and range calculations are correct.
- [ ] **Verify preview:** all discovered site URLs and assets; 100% known video links; no errors from malformed methods or Range; HTTPS; optionally load test within rate limits. Confirm `X-Raven-Migration-Stage: r2` for samples including MP4 and JPG.
- [ ] **Safe deploy:** promote reviewed Worker version with rollback pinned; recheck apex and www plus video links immediately; if failure roll back the Worker without altering Buffer.
- [ ] **Commit:** `feat(cloudflare): serve complete Raven Crow library from R2`.

### Task 5 — ensure article, image and section fidelity

**Files:** Tests `tests/cloudflare/content-integrity.test.mjs`; reuse `public/editorial-feed.json`, `public/noticias.json`, `public/editorial-images.json`, `public/coluna-ensaios.json` and existing builders. Only modify editorial data with independently verified facts and review.

**Interfaces:** Consumes published manifest from Task 2 and build outputs; produces `validateSiteContent(rootDir): { errors: string[]; pages: number; articles: number }`.

- [ ] **RED:** Reproduce invalid trailing `\\n` JSON; duplicate article ID; feed points to missing HTML; broken image/credit; missing column/books index; missing Google verification file; orphan article incorrectly included in sitemap.
- [ ] **Verify RED:** `node --test tests/cloudflare/content-integrity.test.mjs`.
- [ ] **Implement:** validate published article IDs and canonicity, keep homepage limited preview and `noticias.html` full archive, preserve Column, Books, media assets and approved card layout. Fail build with actionable diagnostics on malformed JSON; do not silently suppress news.
- [ ] **Verify:** existing Python full builder/test pipeline plus new tests. URL list from feed has no 404; JSON-LD and article dates legitimate; photo copyright/credits intact.
- [ ] **Commit:** `test(editorial): enforce publication integrity for Cloudflare deployment` (and isolated bugfix commits if needed).

### Task 6 — continuous delivery from GitHub main to Cloudflare

**Files:** Create `.github/workflows/cloudflare-site-release.yml` and `ops/cloudflare/release.mjs` plus tests `tests/cloudflare/release.test.mjs`. Read existing `.github/workflows/news-pages.yml` before any change.

**Interfaces:**
- Consumes deterministic Git ref + validated build output + `syncMedia`.
- Produces `releaseSite({ commitSha, dryRun, canary }): Promise<{ deployedSha: string; manifestSha: string; healthChecksPassed: boolean }>`.

- [ ] **RED:** Tests reject unknown SHA, changed Git HEAD mid-run, missing/invalid HTML, concurrent release, failed R2 sync, test failure, failed apex health; prevent mutating live Worker on failed gates.
- [ ] **Verify RED:** `node --test tests/cloudflare/release.test.mjs`.
- [ ] **Implement:** separate editorial generation from deployment. Reuse existing four Python builders and ``news-pages.yml` output; **avoid self-triggering infinite commit loops**. Sync all generated assets to R2 from a pinned commit before promoting Worker. GitHub Environment secrets scoped to Cloudflare and limited R2 bucket, never on untrusted PR runs.
- [ ] **Verify:** PR dry run builds and tests without secrets; sandbox staging deploy; one safe article addition triggers release once, updates site and sitemap, no duplicate media upload. Produce a release summary with commit SHA, R2 manifest SHA, changed files and health checks.
- [ ] **Commit:** `ci(cloudflare): gated Raven Crow site and R2 deployment`.

### Task 7 — safe bridge for future video URLs, without changing the cutter

**Files:** Create an isolated contract/document `ops/cloudflare/video-handoff-contract.md` and `tests/cloudflare/video-url.test.mjs`. **Do not modify n8n/daemon/ReservaGPT/Buffer here.**

**Interfaces:** `verifyPublishedVideo(url: string, expectedSha256: string, expectedBytes: number): Promise<{ ok: boolean; headStatus: number; rangeStatus: number; mime: string }>`.

- [ ] **RED:** Tests for queued URL not on R2, wrong bytes or hash, duplicate hash, missing Range, future source file not yet uploaded; all prevent claiming "ready".
- [ ] **Verify RED:** `node --test tests/cloudflare/video-url.test.mjs`.
- [ ] **Implement contract:** future MP4s get unique SHA256, are uploaded to R2 before downstream publication, and keep `https://ravencrow.cloud/clips/<sha>.mp4`; use read-only reconciliation against existing local media/private publication ledgers to avoid duplicate Buffer schedules.
- [ ] **Prove contract:** upload one QA-approved test file through a **separate** authorized publication dry-run; read and validate from public URL; do not schedule/post it. Record exact handoff requirements for owner of the existing local transport to adopt in a later release.
- [ ] **Commit:** `docs(cloudflare): define verified media URL handoff`.

### Task 8 — SEO, analytics, ads and full page regression

**Files:** Existing `raven_seo.py`, `public/robots.txt`, `public/sitemap.xml`, `public/raven-analytics.js`, `public/raven-posthog.json`, `public/ads.txt` and existing tests; new `tests/cloudflare/public-pages.test.mjs`.

- [ ] **RED:** Test missing sitemap page, canonical mismatch with apex, missing schema `Article`/`WebSite`, missing Google verification HTML, broken PostHog instrumentation, blocked CSS, ad labels missing/incorrect.
- [ ] **Verify RED:** `node --test tests/cloudflare/public-pages.test.mjs`.
- [ ] **Implement only needed repairs:** preserve original ads, PIX and bookstore links; do not invent advertiser conversions; keep content unchanged and metadata accurate. Cache HTML/JSON briefly, immutable hashed media longer; implement controlled invalidation of changed URLs.
- [ ] **Verify:** all sitemap URLs HTTP 200 over apex and www, stable canonical policy, mobile/desktop smoke check, no ad script breakage, Search Console access remains valid. Report indexing separately from HTTP availability.
- [ ] **Commit:** `test(cloudflare): enforce SEO, analytics and ads parity`.

### Task 9 — observability, rollback and operational ownership

**Files:** Create `docs/cloudflare-migration/RUNBOOK.md`, `docs/cloudflare-migration/OPERATIONS-LEDGER.md` (no secrets), `ops/cloudflare/health-check.mjs`, tests `tests/cloudflare/health-check.test.mjs`. Optional GitHub workflow for scheduled reporting **only** when clearly desired and authorized; do not create another autonomous content agent.

- [ ] **RED:** Simulate apex 503, R2 missing MP4, malformed feed, GitHub Raw fallback in production, 5xx spike, certificate error and rollback attempt; alerts/release gates must detect these.
- [ ] **Verify RED:** `node --test tests/cloudflare/health-check.test.mjs`.
- [ ] **Implement:** smoke health for apex, www, site pages, 12+ news items, video HEAD/Range, R2 inventory delta, GitHub releases and Cloudflare error logs. Define responsible operator and escalation path without new unnecessary daemons.
- [ ] **Write rollback:** retain prior Worker version, DNS snapshot, R2 object inventory/manifest, Git commit. Roll back routing/Worker version on failed release; **do not** assume suspended Render is viable; preserve old objects.
- [ ] **Verify:** deliberately fail health check in staging and observe nonzero exit; restore and get clean output. Publish concise runbook in repo.
- [ ] **Commit:** `docs(cloudflare): production runbook, health checks and rollback`.

## Release gates (must all be true before "migração completa")

- [ ] Zone active and both apex and www HTTPS return 200 without `x-render-routing`.
- [ ] Every canonical sitemap URL and every feed article loads HTTP 200; the feed JSON parses and content/images are approved.
- [ ] All tracked static assets and all existing video objects migrated and integrity-checked; **R2 inventory = source manifest, zero missing/mismatch**, no unapproved deletion.
- [ ] Worker serves tested MP4 from **R2**, not `github-fallback`, including HEAD, GET, Range=206 and invalid Range=416.
- [ ] Automatic deployments use pinned SHA and green tests, with one verified new-article release. No hidden cloud-write scripts or upload endpoints exposed.
- [ ] Media URLs already in Buffer remain usable; no duplicate posts, no changed agent schedules.
- [ ] SEO and PostHog/ads/book/library/column parity verified; rollback procedure tested.
- [ ] After these gates pass: switch off the temporary GitHub Raw fallback; preserve a safe, versioned rollback, and only then consider retiring Render. Never delete Render or GitHub materials automatically.

## Commands and proof for each task

- Baseline (in clean worktree): `python build-raven.py`; `python build-column.py`; `python build-news-index.py`; `python build-library.py`; `python -m unittest discover -s tests -q`; `node --check public/raven-frontpage.js`; `node --check public/raven-books.js`; `node --check public/raven-column.js`.
- Cloudflare tests: `node --test tests/cloudflare/*.test.mjs` (once created); `git diff --check` and source/binary manifest comparison.
- External checks: `curl -sSI https://ravencrow.cloud/`, `curl -sSI https://www.ravencrow.cloud/`, `curl -sSI https://ravencrow.cloud/sitemap.xml`, `curl -sSI https://ravencrow.cloud/editorial-feed.json`, `curl -sSI -H "Range: bytes=0-15" https://ravencrow.cloud/clips/<known-sha>.mp4`.
- For each task: log **RED result**, **GREEN result**, git commit hash, Cloudflare Worker version, R2 object counts, user-facing impact and rollback steps.
- If the full existing suite fails for an unrelated preexisting issue, record exact failure and isolate root cause; NEVER claim "all tests passed" or bypass it.

## Execution priorities and ownership after handoff

**P0 immediately:** Claude fixes the apex 503 and independently verifies site accessibility.

**P1 after P0:** Claude completes R2 import for the remaining assets and all MP4s; restores image coverage; then verifies no GitHub Raw dependency. Cloudflare handles web delivery; other services continue unchanged.

**P2:** Claude implements repeatable GitHub -> Cloudflare CI/CD, caching, health checks and safe rollback. This replaces manual website deploy work, **not** n8n or editorial agency.

**P3:** Claude coordinates with the original transport owner on publishing new MP4s to R2 before Buffer, preserving URL and scheduling. Do not modify operational agents without a separately reviewed implementation plan.

**Weekly operational report:** current live commit, site uptime, apex/www health, indexed sitemap count (not claimed Google indexing), R2 object count/missing media, recent deployment errors, outstanding blockers and rollback readiness.

## Deliverable format back to owner

At the end of each task, report exactly:
1. What was changed (files, Cloudflare objects, route/DNS changes) and what was deliberately NOT changed.
2. Proof: baseline and new test counts, curl statuses, Worker revision, Git SHA, R2 SHA/byte verification and URL tested.
3. Remaining blockers, risks, incident response and whether any automated publishing changed.
4. Next task, executable next command, and rollback location.

**Do not mark this handoff "done" until Task 9 and release gates are satisfied.**
