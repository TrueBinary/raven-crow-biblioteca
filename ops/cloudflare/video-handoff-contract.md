# Raven Crow — video URL handoff contract (Cloudflare)

Owner of this contract: site hosting (Cloudflare). Owner of the producer: the cut pipeline in `D:\CorteFlow` (`config/raven-site-media.mjs`, `config/raven-buffer-handoff.mjs`). **This document changes nothing in the pipeline**; it states what the hosting side guarantees and what a future pipeline release must adopt.

## URL

- Public URL: `https://ravencrow.cloud/clips/<sha256>.mp4` or `https://www.ravencrow.cloud/clips/<sha256>.mp4` (both served by Worker `raven-crow-site-production`). The pipeline currently uses the `www` form (`RAVEN_CLIPS_BASE`).
- `<sha256>` is the SHA-256 of the exact MP4 bytes. A key is written once and never overwritten or deleted; a changed video gets a new hash and a new URL.
- Thumbnail: same path with `.jpg`.

## "Ready" definition

A clip is ready for Buffer only when `node ops/cloudflare/video-url.mjs <url> <sha256> <bytes>` exits 0, which means:

1. URL matches the pattern above and the hash in the URL equals the expected hash;
2. `HEAD` → 200, `Content-Type: video/mp4`, `Content-Length` = expected bytes, `X-Raven-Migration-Stage: r2`;
3. `Range: bytes=0-15` → 206 with `Content-Range: bytes 0-15/<bytes>`;
4. full `GET` SHA-256 equals the expected hash.

`findDuplicateClips()` in the same module reports two queue entries pointing at the same hash.

## How a clip reaches R2 today

1. Pipeline commits `public/clips/<sha>.mp4` + `.jpg` to GitHub `main` and pushes (`uploadApprovedToSite`).
2. Release (`ops/cloudflare/release.mjs`) syncs `main` to R2 with integrity checks. While GitHub Actions is locked it runs from the Windows task "Raven Crow - release site R2" every 15 minutes (`ops/cloudflare/release-local.ps1`).
3. Until step 2 runs, the Worker serves the clip from GitHub Raw (`X-Raven-Migration-Stage: github-fallback`) because `GITHUB_FALLBACK=1`.

## Why the GitHub fallback must stay on for now

`waitForSiteMedia` waits at most 18 × 10 s = 3 min after the push and only checks HEAD/Range (not the stage header). Release runs up to 15 min later. With the fallback off, new clips would fail with `SITE_DEPLOY_NOT_READY` and not be scheduled.

## Requirements for the pipeline owner (a separate, reviewed release)

To turn the fallback off, the pipeline must do **one** of these, then wait for the "Ready" check above before calling Buffer:

- (preferred) after pushing, run the release once for the pushed commit (`release.mjs <sha>` from a no-checkout worktree), then verify; or
- extend its wait to ≥ 20 min and additionally require `X-Raven-Migration-Stage: r2`.

Also: never reuse a hash for different bytes, never schedule the same hash twice (use `findDuplicateClips` on the pending queue), and keep the ledger's `mediaHash` equal to the URL hash.

## Evidence (2026-11-07)

- 49 already-sent clip URLs from `data/buffer-hourly-ledger.json`: 49/49 HEAD 200 served from `r2`.
- 4 future queued clips (20h, 21h, 22h, 23h UTC): 4/4 ready by the full check (size, Range, SHA-256).
- No duplicate hashes in the future queue.
