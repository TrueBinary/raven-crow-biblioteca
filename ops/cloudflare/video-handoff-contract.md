# Raven Crow — video URL handoff contract (Cloudflare)

Owner of this contract: site hosting (Cloudflare). Owner of the producer: the cut pipeline in `D:\CorteFlow` (`config/raven-site-media.mjs`, `config/raven-buffer-handoff.mjs`). **This document changes nothing in the pipeline**; it states what the hosting side guarantees and what a future pipeline release must adopt.

## URL

- Public URL: `https://ravencrow.cloud/clips/<sha256>.mp4` or `https://www.ravencrow.cloud/clips/<sha256>.mp4` (both served by Worker `raven-crow-site-production`). The pipeline currently uses the `www` form (`RAVEN_CLIPS_BASE`).
- `<sha256>` is the SHA-256 of the exact MP4 bytes. A key is written once and never overwritten (it is deleted only when retired after posting); a changed video gets a new hash and a new URL.
- Thumbnail: same path with `.jpg`.

## "Ready" definition

A clip is ready for Buffer only when `node ops/cloudflare/video-url.mjs <url> <sha256> <bytes>` exits 0, which means:

1. URL matches the pattern above and the hash in the URL equals the expected hash;
2. `HEAD` → 200, `Content-Type: video/mp4`, `Content-Length` = expected bytes, `X-Raven-Migration-Stage: r2`;
3. `Range: bytes=0-15` → 206 with `Content-Range: bytes 0-15/<bytes>`;
4. full `GET` SHA-256 equals the expected hash.

`findDuplicateClips()` in the same module reports two queue entries pointing at the same hash.

## How a clip reaches R2 today (since 2026-11-11)

1. `uploadApprovedToSite` in `D:\CorteFlow\configaven-site-media.mjs` PUTs `clips/<sha>.mp4` and `.jpg` straight into the R2 bucket `raven-crow-media` (REST API, cf CLI login; `config/raven-r2.mjs`), checks size + MD5 ETag, then waits for the public URL. Clips no longer go through git: each one used to stay in the repository history forever (4+ GB).
2. `config/raven-clip-retire.mjs` (daily, 06:30) lists `clips/` in R2 and deletes clips already posted on every destination; for old clips still tracked in git it does `git rm` first, so the site sync cannot upload them again.
3. The site sync (`r2-sync.mjs`) never deletes anything: clips that exist only in R2 are not its business.

## Requirements for the pipeline owner (a separate, reviewed release)

To turn the fallback off, the pipeline must do **one** of these, then wait for the "Ready" check above before calling Buffer:

- (preferred) after pushing, run the release once for the pushed commit (`release.mjs <sha>` from a no-checkout worktree), then verify; or
- extend its wait to ≥ 20 min and additionally require `X-Raven-Migration-Stage: r2`.

Also: never reuse a hash for different bytes, never schedule the same hash twice (use `findDuplicateClips` on the pending queue), and keep the ledger's `mediaHash` equal to the URL hash.

## Evidence (2026-11-07)

- 49 already-sent clip URLs from `data/buffer-hourly-ledger.json`: 49/49 HEAD 200 served from `r2`.
- 4 future queued clips (20h, 21h, 22h, 23h UTC): 4/4 ready by the full check (size, Range, SHA-256).
- No duplicate hashes in the future queue.
