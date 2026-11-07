# Raven Crow — Regression Tests and Agent Smoke Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans. Check tasks and avoid unreviewed changes to production.

**Goal:** Resolve five failing regression checks without changing running n8n, daemon or Buffer publication logic; verify impacted agents after GitHub became private.

**Architecture:** Render + ravencrow.cloud remains the only public site/media endpoint; GitHub remains private. Photos need verified Commons license; generating a branded SVG cover does not authorize calling it a photograph. n8n, video pipeline and Buffer publisher code are immutable in this plan.

**Tech Stack:** Python unittest, SVG cover generator, Node native tests, PowerShell harness, Git worktree, GitHub, Render, Buffer.

**Spec:** docs/superpowers/specs/2026-11-06-raven-dns-ig-media.md

## Approaches
- Recommended: correct outdated test expectations, rebuild deterministic editorial covers and enforce verified photo attribution; zero new services.
- Rejected: change daemon priority/ACK and Buffer expiration rules to satisfy obsolete tests.
- Rejected: invent unlicensed photographs for three newer articles.

## Global Constraints
- Do not restart/modify n8n, daemon, CorteFlow runtime scripts, Buffer schedules, or Cloudflare/DNS.
- No hard reset/rebase/force push; isolate site changes to worktree fix/raven-regression-20261107.
- Agent probes must not create duplicate posts or fabricated news.
- Backups for three Node test files: D:\RavenNewsEngine\backups\regression-20261107.

## Review Focus
- Test fixtures depend on wall clock (48-hour expiration): deterministic fixed now.
- Priority logic prefers fresh queued jobs with fewer than two active: test exactly that and retain old processing eligibility.
- Hourly ACK writes a sidecar by-slot: assert both files without treating directory as ACK.
- New articles have no licensed Commons photo: do not fabricate; validate original seven curated licenses and any future license.
- Existing generator creates SVG cover for every valid article: regenerate stale catalog; preserve original photographs.
- GitHub is private: agent images served by ravencrow.cloud after HEAD/GET before Buffer.

### Task 1 — Node tests
- [x] Reproduce red tests individually.
- [x] Back up originals with hashes.
- [x] Fix stale test expectations only, not runtime modules.
- [x] Verify targeted tests: 16/16, 11/11, 6/6.
- [x] Run all 85 Node test files: 416/416 passing, no daemon runtime modifications; patch stored at docs/superpowers/patches/corteflow-tests-20261107.patch.

### Task 2 — Editorial site artifacts
- [x] Reproduce two red tests in isolated worktree.
- [x] Generated three missing SVG covers with editorial_covers.build_covers; 10/10 covers passed XML parsing.
- [x] Updated editorial-images.json preserving carousels/photos.
- [x] Corrected photo test scope to seven curated originals and verified attribution; no fake new photos.
- [x] Site suite: 62/62 passing; 3/3 JavaScript syntax checks passing.
- [ ] Commit/push only if all suite checks pass and HEAD parent equals origin/main.

### Task 3 — Agent smoke
- [ ] Instagram renderer + transport, blocked manifest guard, public assets and Buffer IDs.
- [ ] Corvo Investigador public JSON + breaking validator, no fabricated news.
- [ ] ReservaGPT video HEAD/Range, Git private credentials, local mode/locks; no duplication.
- [ ] Render deployment, n8n /healthz, DNS.
- [ ] Run affected enabled automations explicitly and report run state, not assumed completion.

### Task 4 — Fallback
- [ ] Summarize verified outcomes and remaining limitations.
- [ ] If Render/DNS fail stop Buffer post and preserve media/manifest; don't use Raw.
- [ ] No modifications to running video pipeline.
