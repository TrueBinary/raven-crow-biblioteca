// Source (Git tree) vs destination (R2) inventory for the Raven Crow site.
import { execFileSync, spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { mimeFor } from './raven-production-worker.mjs';

const SAFE_KEY = /^[A-Za-z0-9._\/-]+$/;
const SECRET = /(^|\/)(\.env[^/]*|\.git\/.*|.*\.pem|.*\.key|id_rsa.*)$/;

export const keyFor = path => {
  const key = path === 'index.html' ? 'index.html' : path.replace(/^public\//, '');
  if (!SAFE_KEY.test(key) || key.includes('..') || key.startsWith('/') || key.startsWith('__migration/')) throw Error('unsafe key: ' + path);
  return key;
};

function sha256Blob(repo, oid) {
  return new Promise((resolve, reject) => {
    const h = createHash('sha256');
    const p = spawn('git', ['-C', repo, 'cat-file', 'blob', oid]);
    p.stdout.on('data', d => h.update(d));
    p.on('error', reject);
    p.on('close', code => (code === 0 ? resolve(h.digest('hex')) : reject(Error('git cat-file failed for ' + oid))));
  });
}

export async function getSourceManifest(gitRef, { repo = process.cwd() } = {}) {
  const tree = execFileSync('git', ['-C', repo, 'ls-tree', '-r', '-l', gitRef, '--', 'index.html', 'public'], { encoding: 'utf8', maxBuffer: 64 << 20 }).trimEnd();
  const out = [], seen = new Set();
  for (const line of tree ? tree.split('\n') : []) {
    const m = /^\d+ blob ([a-f0-9]+)\s+(\d+)\t(.+)$/.exec(line);
    if (!m) throw Error('unknown git tree entry: ' + line.slice(0, 120));
    const [, oid, size, path] = m;
    if (SECRET.test(path)) continue;
    const key = keyFor(path);
    if (seen.has(key)) throw Error('key collision: ' + key);
    seen.add(key);
    out.push({ key, size: Number(size), sha256: await sha256Blob(repo, oid), mime: mimeFor(key) });
  }
  return out;
}

// Cloudflare R2 REST listing ignores `limit`; it pages by per_page + cursor.
export async function listR2All({ accountId, bucket, token, fetchImpl = fetch }) {
  const all = [];
  let cursor = '';
  for (let page = 0; page < 10000; page++) {
    const u = new URL(`https://api.cloudflare.com/client/v4/accounts/${accountId}/r2/buckets/${bucket}/objects`);
    u.searchParams.set('per_page', '1000');
    if (cursor) u.searchParams.set('cursor', cursor);
    const res = await fetchImpl(u.href, { headers: { Authorization: 'Bearer ' + token } });
    const body = await res.json().catch(() => null);
    if (!res.ok || !body?.success) throw Error('R2 list failed: HTTP ' + res.status);
    for (const o of body.result) all.push({ key: o.key, size: Number(o.size), etag: o.etag });
    const info = body.result_info || {};
    const truncated = info.is_truncated === true || info.is_truncated === 'true';
    if (!truncated) return all;
    if (!info.cursor || info.cursor === cursor) throw Error('R2 list truncated without a new cursor after ' + all.length + ' objects');
    cursor = info.cursor;
  }
  throw Error('R2 list did not terminate');
}

export function diffManifests(source, destination) {
  const dest = new Map(destination.map(o => [o.key, o]));
  const missing = [], different = [], matching = [];
  for (const s of source) {
    const d = dest.get(s.key);
    if (!d) missing.push(s.key);
    else if (d.size !== s.size) different.push(s.key);
    else matching.push(s.key);
  }
  return { missing, different, matching };
}

if (import.meta.url === `file:///${process.argv[1]?.replace(/\\/g, '/')}` || import.meta.url === `file://${process.argv[1]}`) {
  const ref = process.argv[2] || 'origin/main';
  const src = await getSourceManifest(ref);
  const sha = execFileSync('git', ['rev-parse', ref], { encoding: 'utf8' }).trim();
  const summary = { gitRef: ref, commit: sha, files: src.length, bytes: src.reduce((a, x) => a + x.size, 0), mp4: src.filter(x => x.key.endsWith('.mp4')).length };
  const { CLOUDFLARE_ACCOUNT_ID: accountId, CLOUDFLARE_API_TOKEN: token } = process.env;
  if (accountId && token) {
    const r2 = await listR2All({ accountId, bucket: 'raven-crow-media', token });
    const d = diffManifests(src, r2);
    Object.assign(summary, { r2Objects: r2.length, r2Bytes: r2.reduce((a, x) => a + x.size, 0), missing: d.missing.length, different: d.different, matching: d.matching.length });
  }
  console.log(JSON.stringify({ summary, manifest: process.argv.includes('--full') ? src : undefined }, null, 1));
}
