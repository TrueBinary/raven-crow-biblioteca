# Raven Crow — Workers Builds Deploy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every push to `main` builds the Raven Crow site on Cloudflare Workers Builds (builders + validation + R2 sync + Worker deploy), replacing the locked GitHub Actions and the Windows task.

**Architecture:** A Node orchestrator (`build-and-release.mjs`) is the Workers Builds build command: hydrate published photos from R2 → run the 4 Python builders → validate the built directory → phased delete-free sync of the directory to R2 → health check. `npx wrangler deploy` with a committed `wrangler.jsonc` is the deploy command. Existing modules gain a *directory* source next to their *Git* source.

**Tech Stack:** Node 24 (ESM, `node:test`), Python 3.14 stdlib builders, Cloudflare R2 REST API, Wrangler, Workers Builds.

**Spec:** `docs/superpowers/specs/2026-11-07-workers-builds-deploy-design.md`

## Global Constraints

- R2 bucket `raven-crow-media`; Worker `raven-crow-site-production`; account `f6140a337d3b05e5e27c7f64ed166134`; routes `ravencrow.cloud/*`, `www.ravencrow.cloud/*` (zone `ravencrow.cloud`); compatibility date `2026-11-07`; var `GITHUB_FALLBACK = "1"`.
- Build secret `R2_API_TOKEN`, build var `CLOUDFLARE_ACCOUNT_ID`; token never printed, never committed.
- Never delete R2 objects; media keys (non-`isMutable`) never overwritten; phased upload (`phaseOf`) unchanged.
- Validation errors abort before any write; build exits non-zero so Workers Builds skips the deploy command.
- Builders run unmodified (`build-raven.py`, `build-column.py`, `build-news-index.py`, `build-library.py`, in that order).
- Tests: `RAVEN_OFFLINE=1 node --test "tests/cloudflare/*.test.mjs"` stays green (81 pass + 3 skipped at start).

## Review Focus

1. **Photo hydration mismatch:** R2 has a photo but not its credit entry (or the reverse) → builder must not pick a new photo for that slug silently; hydration restores both or neither (Task 3 test `hydrates photo and credit together`).
2. **Builder failure mid-run** (Commons timeout, Python exception) → build fails, nothing synced (Task 4 test `builder failure aborts before sync`).
3. **Untracked junk in the build directory** (`.git`, `__pycache__`, `node_modules`, `.wrangler`) → never uploaded (Task 1 test `dir manifest skips junk and secrets`).
4. **Generated file differs from what R2 has for an immutable key** (e.g. a regenerated photo) → sync aborts with a clear reason, no overwrite (Task 1 test `dir source keeps immutable rule`).
5. **Wrangler config drift** (binding, var or route missing) → deploy would break production; config test pins every value (Task 5).

---

### Task 1: Directory source for manifest and sync

**Files:**
- Modify: `ops/cloudflare/inventory.mjs`, `ops/cloudflare/r2-sync.mjs`
- Test: `tests/cloudflare/inventory.test.mjs`, `tests/cloudflare/r2-sync.test.mjs`

**Interfaces:**
- Produces: `getDirManifest(root: string): Promise<Array<{key,size,sha256,mime}>>` (inventory.mjs) — walks `index.html` and `public/**` with the same `keyFor`/secret rules as `getSourceManifest`, skipping directories `.git`, `__pycache__`, `node_modules`, `.wrangler`.
- Produces: `syncMedia({ source, api, dryRun, only, maxConcurrency, retryDelayMs, log })` where `source = { commit: string, manifest(): Promise<Entry[]>, read(key: string): Buffer }`; helpers `gitTreeSource(gitRef, repo)` and `dirTreeSource(root, label)` exported from r2-sync.mjs. `gitRef`/`repo` params keep working (they build a `gitTreeSource`) so existing callers and tests are untouched.

- [ ] **Step 1: Write failing tests**
  - `dir manifest skips junk and secrets`: temp dir with `index.html`, `public/a.txt`, `public/.env`, `public/__pycache__/x.pyc`, `node_modules/x.js` → keys `['a.txt','index.html']`, sha256 of `a.txt` correct.
  - `dir source uploads built files`: temp dir with a generated `public/noticias/nova-2026/index.html` → `syncMedia({ source: dirTreeSource(dir,'build'), api: fakeApi() })` puts `noticias/nova-2026/index.html`, `result.commit === 'build'`.
  - `dir source keeps immutable rule`: fake R2 holds `editorial/photos/x.jpg` with other bytes → `failed[0].reason` matches `/differs/`, no puts.
- [ ] **Step 2: Run** `RAVEN_OFFLINE=1 node --test tests/cloudflare/inventory.test.mjs tests/cloudflare/r2-sync.test.mjs` — Expected: the 3 new tests FAIL (`getDirManifest`/`dirTreeSource` not exported).
- [ ] **Step 3: Implement** `getDirManifest`, `gitTreeSource`, `dirTreeSource`; inside `syncMedia` replace `getSourceManifest(...)`/`readBlob(...)` with `source.manifest()`/`source.read(key)`; the "source changed during sync" check compares against the manifest entry as today.
- [ ] **Step 4: Run** the full suite — Expected: all pass (81 + 3 new).
- [ ] **Step 5: Commit** `feat(cloudflare): directory source for manifest and R2 sync`

### Task 2: Directory source for validators

**Files:**
- Modify: `ops/cloudflare/content-integrity.mjs`
- Test: `tests/cloudflare/content-integrity.test.mjs`

**Interfaces:**
- Consumes: nothing new.
- Produces: `dirSource(root: string): { exists(p): boolean, read(p): string }` reading repo-relative paths (`index.html`, `public/...`) from disk; used by both `validateSiteContent` and `validatePublicPages` (they already take a `src`).

- [ ] **Step 1: Write failing test** `dirSource reads the built tree`: write the minimal valid site files from the existing `site()` fixture to a temp dir → `validateSiteContent(dirSource(dir)).errors` deep-equals `[]`; delete `public/coluna.html` → errors match `/coluna\.html missing/`.
- [ ] **Step 2: Run** the file — Expected: FAIL (`dirSource` not exported).
- [ ] **Step 3: Implement** `dirSource` with `fs.existsSync`/`readFileSync(…,'utf8')` under `root`; reject paths containing `..`.
- [ ] **Step 4: Run** full suite — Expected: pass.
- [ ] **Step 5: Commit** `feat(cloudflare): validators read a built directory`

### Task 3: Hydrate published photos from R2

**Files:**
- Create: `ops/cloudflare/hydrate.mjs`
- Modify: `ops/cloudflare/r2-sync.mjs` (add `get(key): Promise<Buffer|null>` to `cloudflareApi`; token lookup order `R2_API_TOKEN`, `CLOUDFLARE_API_TOKEN`, cf CLI login)
- Test: `tests/cloudflare/hydrate.test.mjs`

**Interfaces:**
- Consumes: `cloudflareApi().list()` / `.get(key)`.
- Produces: `hydrateFromR2({ root: string, api }): Promise<{ restored: string[], kept: string[] }>` — for every R2 key `editorial/photos/<slug>.jpg` whose slug is in R2's `editorial-photo-credits.json` and whose file is missing locally, writes `public/editorial/photos/<slug>.jpg`; merges those credit entries into local `public/editorial-photo-credits.json` (local entries win when the local photo file exists). Photos without a credit entry in R2 are not restored.

- [ ] **Step 1: Write failing tests** (fake api with `list`/`get`):
  - `hydrates photo and credit together`: R2 has `editorial/photos/a.jpg` + credits `{a:{…}}`, local has neither → file written, local credits gain `a`, `restored` = `['editorial/photos/a.jpg']`.
  - `keeps local photo and credit`: local has `b.jpg` + credit `b` → untouched, in `kept`.
  - `skips photo without credit`: R2 has `c.jpg` but credits lack `c` → not written.
  - `no R2 credits file`: returns `{restored:[],kept:[]}` without throwing.
- [ ] **Step 2: Run** `node --test tests/cloudflare/hydrate.test.mjs` — Expected: FAIL (module missing).
- [ ] **Step 3: Implement** `hydrateFromR2` and `cloudflareApi().get` (REST `GET …/r2/buckets/<bucket>/objects/<key>`, 404 → `null`).
- [ ] **Step 4: Run** full suite — Expected: pass.
- [ ] **Step 5: Commit** `feat(cloudflare): hydrate published photos and credits from R2 before building`

### Task 4: Build-and-release orchestrator

**Files:**
- Create: `ops/cloudflare/build-and-release.mjs`
- Test: `tests/cloudflare/build-and-release.test.mjs`

**Interfaces:**
- Consumes: `hydrateFromR2` (T3), builders via `runBuilders(root)`, `validateSiteContent`/`validatePublicPages` + `dirSource` (T2), `syncMedia` + `dirTreeSource` (T1), `verifyHost`.
- Produces: `buildAndRelease({ root, label, dryRun, deps }): Promise<{ restored:number, synced:{uploaded,updated,skipped}, warnings:string[], healthChecksPassed:boolean|null }>`; CLI `node ops/cloudflare/build-and-release.mjs [--dry-run]` uses `process.cwd()`, label = `WORKERS_CI_COMMIT_SHA` env or `git rev-parse HEAD`, exits 1 on any thrown error and prints `BUILD BLOCKED: <reason>`. `deps` overrides `hydrate`, `runBuilders`, `validate`, `sync`, `verify`.

- [ ] **Step 1: Write failing tests** (all deps faked):
  - `happy path runs steps in order`: call order `hydrate, builders, validate, sync, verify`; returns `healthChecksPassed: true`.
  - `builder failure aborts before sync`: `runBuilders` throws → rejects `/build-raven\.py|builder/`, `sync` never called.
  - `validation errors abort before sync`: validate returns `{errors:['x missing']}` → rejects `/x missing/`, no sync.
  - `sync failure fails the build`: sync returns `failed:[{key:'k',reason:'r'}]` → rejects `/k \(r\)/`, verify not called.
  - `dry run does not write or verify`: sync called with `dryRun:true`, verify not called, `healthChecksPassed: null`.
- [ ] **Step 2: Run** the file — Expected: FAIL (module missing).
- [ ] **Step 3: Implement**; `runBuilders(root)` spawns `python` (or `python3` when `python` is absent) for each builder in order with `cwd: root`, throwing `builder <name> exited <code>` on non-zero; validate = both validators on `dirSource(root)`, errors concatenated, warnings logged.
- [ ] **Step 4: Run** full suite; then local dry run against a fresh checkout: `git -C /d/CorteFlow/work/raven-builder-outputs-20261107 fetch origin main && git -C … reset --hard origin/main` then from that worktree `CLOUDFLARE_ACCOUNT_ID=… node /d/CorteFlow/work/raven-cf-handoff-20261107/ops/cloudflare/build-and-release.mjs --dry-run` — Expected: exit 0, `errors` none, planned uploads only for generated/changed files.
- [ ] **Step 5: Commit** `feat(cloudflare): build-and-release orchestrator for Workers Builds`

### Task 5: Wrangler config for the deploy command

**Files:**
- Create: `wrangler.jsonc`, `package.json` (`"type":"module"`, `"private":true`, devDependency `wrangler` pinned to an exact version ≥ 2 weeks old), `.gitignore` entry `node_modules/`, `.wrangler/`
- Test: `tests/cloudflare/wrangler-config.test.mjs`

**Interfaces:**
- Produces: deploy configuration equal to the live Worker.

- [ ] **Step 1: Write failing test** `wrangler config matches production`: parse `wrangler.jsonc` (strip `//` comments) → `name === 'raven-crow-site-production'`, `main === 'ops/cloudflare/raven-production-worker.mjs'`, `compatibility_date === '2026-11-07'`, `r2_buckets` deep-equals `[{binding:'RAVEN_MEDIA',bucket_name:'raven-crow-media'}]`, `vars.GITHUB_FALLBACK === '1'`, `routes` contains `{pattern:'ravencrow.cloud/*',zone_name:'ravencrow.cloud'}` and `{pattern:'www.ravencrow.cloud/*',zone_name:'ravencrow.cloud'}`, no `assets` key.
- [ ] **Step 2: Run** — Expected: FAIL (file missing).
- [ ] **Step 3: Create** the files with those values.
- [ ] **Step 4: Run** full suite, then `npm install && npx wrangler deploy --dry-run --outdir .wrangler/dry` — Expected: bundle built, bindings listed `RAVEN_MEDIA (raven-crow-media)` and `GITHUB_FALLBACK`, no upload.
- [ ] **Step 5: Commit** `build(cloudflare): wrangler config mirroring the production Worker`; update `docs/cloudflare-migration/RUNBOOK.md` (Workers Builds becomes the release path; Windows task kept as fallback) in the same commit.

### Task 6: Connect Workers Builds and prove one release (owner + executor)

**Files:**
- Modify: `docs/cloudflare-migration/OPERATIONS-LEDGER.md`

- [ ] **Step 1 (owner, dashboard):** Workers & Pages → `raven-crow-site-production` → Settings → Builds → Connect `TrueBinary/raven-crow-biblioteca`, branch `main`; Build command `node ops/cloudflare/build-and-release.mjs`; Deploy command `npx wrangler deploy`; Build watch paths include `*`, exclude `public/clips/*`; build secret `R2_API_TOKEN` (token with Workers R2 Storage: Edit on this account), build variable `CLOUDFLARE_ACCOUNT_ID=f6140a337d3b05e5e27c7f64ed166134`.
- [ ] **Step 2:** Merge the branch to `main` (owner approval). Expected: a build starts. `cf builds triggers list --external-script-id raven-crow-site-production` shows the trigger.
- [ ] **Step 3: Verify the build:** build log shows hydrate count, 4 builders OK, `errors` none, sync summary, health OK, then wrangler deploy OK; record build duration (must be < 20 min; note clone time).
- [ ] **Step 4: Prove a news release:** after the next editorial news commit (do not fabricate one), confirm within one build: the new article page 200, in `/editorial-feed.json`, `/noticias.html`, `/sitemap.xml`; `node ops/cloudflare/health-check.mjs` exit 0.
- [ ] **Step 5:** If no build starts after a push (webhook blocked by the GitHub billing lock), record it, keep the Windows task, stop here. Otherwise record in OPERATIONS-LEDGER: trigger id, first build id, durations; and ask the owner to disable the Windows task "Raven Crow - release site R2" after 3 clean days. Commit `docs(cloudflare): Workers Builds live`.
