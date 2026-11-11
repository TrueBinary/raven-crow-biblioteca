// Idempotent Git -> R2 sync (deletes only retired clips/, see prunePlanned) for the Raven Crow site. Verifies size + MD5 ETag per object.
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { getSourceManifest, listR2All } from './inventory.mjs';

const MAX_PUT = 300 * 1024 * 1024; // REST object PUT limit
const RETIRED_CLIP = /^clips\/[a-f0-9]{64}\.(?:mp4|jpg)$/;
const MAX_PRUNE = 250; // a bad checkout must not wipe the clip store: above this, delete nothing and log
const md5 = b => createHash('md5').update(b).digest('hex');
const srcPath = key => (key === 'index.html' ? 'index.html' : 'public/' + key);
const readBlob = (repo, ref, key) => execFileSync('git', ['-C', repo, 'show', `${ref}:${srcPath(key)}`], { maxBuffer: MAX_PUT + 1 });
// ETag of a single-part R2 upload is the MD5 of the body; multipart ETags contain '-'.
// Site text and generated cover art are rebuilt in place; media (clips, photos) is immutable.
export const isMutable = key => key === 'favicon.ico' || /\.(?:html|json|xml|txt|js|mjs|css)$/.test(key) || /^editorial\/covers\/[a-z0-9-]+\.svg$/.test(key);
const sameContent = (obj, buf) => obj.size === buf.length && (!obj.etag || obj.etag.includes('-') || obj.etag.replace(/"/g, '') === md5(buf));

export async function syncMedia({ gitRef, repo = process.cwd(), api = cloudflareApi(), dryRun = false, only = null, maxConcurrency = 3, retryDelayMs = 2000, log = () => {} }) {
  const commit = execFileSync('git', ['-C', repo, 'rev-parse', gitRef], { encoding: 'utf8' }).trim();
  const source = await getSourceManifest(commit, { repo });
  const dest = new Map((await api.list()).map(o => [o.key, o]));
  const result = { commit, uploaded: 0, updated: 0, skipped: 0, verified: 0, failed: [], planned: [] };

  // Check every existing key first: any conflict aborts before a single write.
  const todo = [];
  for (const s of source) {
    const d = dest.get(s.key);
    if (!d) { todo.push(s); continue; }
    if (!sameContent(d, readBlob(repo, commit, s.key))) {
      if (isMutable(s.key)) { todo.push({ ...s, update: true }); continue; }
      result.failed.push({ key: s.key, reason: `existing object differs (r2 ${d.size} B, git ${s.size} B)` });
    }
    else { result.skipped++; result.verified++; }
  }
  result.planned = todo.map(s => ({ key: s.key, size: s.size, update: !!s.update }));
  // The one exception to delete-free: clips the CorteFlow retirer removed from git after they were posted
  // (config/raven-clip-retire.mjs). Clips only reach R2 through git, so absent from git = retired.
  const inGit = new Set(source.map(s => s.key));
  result.prunePlanned = [...dest.keys()].filter(k => RETIRED_CLIP.test(k) && !inGit.has(k));
  result.pruned = 0;
  if (result.failed.length || dryRun) return result;
  if (only) todo.splice(0, todo.length, ...todo.filter(s => only.has(s.key)));

  // Phases keep links valid mid-sync: media, then pages/assets, then the entry files that link to them.
  // A failed phase stops the run, so the feed never points at an object that did not make it.
  for (const phase of [0, 1, 2]) {
    const batch = todo.filter(s => phaseOf(s.key) === phase);
    await runBatch(batch);
    if (result.failed.length) break;
  }
  if (!result.failed.length && !only) {
    if (result.prunePlanned.length > MAX_PRUNE) log(`prune skipped: ${result.prunePlanned.length} clips > ${MAX_PRUNE}`);
    else for (const key of result.prunePlanned) { await api.delete(key); result.pruned++; log(`DELETED ${key}`); }
  }
  return result;

  async function runBatch(batch) {
    let next = 0;
    await Promise.all(Array.from({ length: Math.max(1, maxConcurrency) }, () => worker()));
    async function worker() {
    while (next < batch.length) {
      const s = batch[next++];
      const buf = readBlob(repo, commit, s.key);
      if (buf.length !== s.size || createHash('sha256').update(buf).digest('hex') !== s.sha256) { result.failed.push({ key: s.key, reason: 'source changed during sync' }); continue; }
      if (buf.length > MAX_PUT) { result.failed.push({ key: s.key, reason: 'larger than REST PUT limit' }); continue; }
      let stored, lastErr;
      for (let attempt = 1; attempt <= 3 && !stored; attempt++) {
        try { stored = await api.put(s.key, buf, s.mime); }
        catch (e) { lastErr = e; if (!(e.status === 429 || e.status >= 500)) break; await new Promise(r => setTimeout(r, retryDelayMs * attempt)); }
      }
      if (!stored) { result.failed.push({ key: s.key, reason: 'upload failed: ' + (lastErr?.message || 'unknown') }); continue; }
      if (!sameContent(stored, buf)) { result.failed.push({ key: s.key, reason: 'verify failed after upload' }); continue; }
      if (s.update) result.updated++; else result.uploaded++;
      result.verified++;
      log(`OK ${s.key} ${s.size}`);
    }
    }
  }
}

const ENTRY = new Set(['index.html', 'editorial-feed.json', 'noticias.json', 'noticias.html', 'coluna.html', 'coluna-ensaios.json', 'livros.html', 'livros.json', 'editorial-images.json', 'sitemap.xml']);
export const phaseOf = key => (ENTRY.has(key) ? 2 : isMutable(key) ? 1 : 0);

// shortcut: falls back to the cf CLI OAuth login file for local runs; CI must set CLOUDFLARE_API_TOKEN.
function token() {
  if (process.env.CLOUDFLARE_API_TOKEN) return process.env.CLOUDFLARE_API_TOKEN;
  return readTokenFile(process.env.APPDATA + '/xdg.config/cloudflare/config/default.json');
}

// The cf CLI rewrites this file when it refreshes the OAuth token; a read can land in that gap.
export function readTokenFile(path, { tries = 20, waitMs = 500 } = {}) {
  for (let i = 1; ; i++) {
    try { return JSON.parse(readFileSync(path, 'utf8')).oauth_token; }
    catch (e) { if (i >= tries) throw e; Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, waitMs); }
  }
}

export function cloudflareApi({ accountId = process.env.CLOUDFLARE_ACCOUNT_ID, bucket = 'raven-crow-media' } = {}) {
  const base = () => `https://api.cloudflare.com/client/v4/accounts/${accountId}/r2/buckets/${bucket}/objects/`;
  return {
    list: () => listR2All({ accountId, bucket, token: token() }),
    async put(key, body, mime) {
      const res = await fetch(base() + key.split('/').map(encodeURIComponent).join('/'), { method: 'PUT', headers: { Authorization: 'Bearer ' + token(), 'Content-Type': mime }, body });
      const j = await res.json().catch(() => null);
      if (!res.ok || !j?.success) { const e = Error('HTTP ' + res.status + ' ' + JSON.stringify(j?.errors || '')); e.status = res.status; throw e; }
      return { key, size: Number(j.result.size), etag: j.result.etag };
    },
    async delete(key) {
      const res = await fetch(base() + key.split('/').map(encodeURIComponent).join('/'), { method: 'DELETE', headers: { Authorization: 'Bearer ' + token() } });
      if (!res.ok && res.status !== 404) throw Error('DELETE ' + key + ' HTTP ' + res.status);
    },
  };
}

if (import.meta.url === `file:///${process.argv[1]?.replace(/\\/g, '/')}` || import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const only = args.find(a => a.startsWith('--only='))?.slice(7).split(',');
  const r = await syncMedia({ gitRef: args.find(a => !a.startsWith('--')) || 'origin/main', dryRun: args.includes('--dry-run'), only: only && new Set(only), log: m => console.error(m) });
  const bytes = r.planned.reduce((a, x) => a + x.size, 0);
  console.log(JSON.stringify({ commit: r.commit, uploaded: r.uploaded, updated: r.updated, skipped: r.skipped, verified: r.verified, failed: r.failed, plannedCount: r.planned.length, plannedBytes: bytes, pruned: r.pruned, prunePlanned: r.prunePlanned.length }, null, 1));
  process.exitCode = r.failed.length ? 2 : 0;
}

