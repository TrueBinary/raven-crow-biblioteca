// Read-only health check for ravencrow.cloud. Exit code 1 when any problem is found.
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import { verifyHost } from './verify-domain.mjs';

const ORIGIN = 'https://ravencrow.cloud';

export async function healthCheck({ fetchImpl = fetch, pages = [], clips = [], inventory = null, minArticles = 12 } = {}) {
  const problems = [], warnings = [];
  const get = (p, init) => fetchImpl(ORIGIN + p, { ...init, signal: AbortSignal.timeout(20000) });

  for (const host of [ORIGIN + '/', 'https://www.ravencrow.cloud/']) {
    const r = await verifyHost(host, { fetchImpl });
    if (!r.ok) problems.push(`${host}: status ${r.status}${r.renderSuspend ? ' (Render suspended)' : ''}${r.error ? ' ' + r.error : ''}${r.tlsOk ? '' : ' tls/https failed'}`);
  }

  try {
    const res = await get('/editorial-feed.json');
    const n = JSON.parse(await res.text()).articles?.length ?? 0;
    if (n < minArticles) problems.push(`feed: only ${n} articles (< ${minArticles})`);
  } catch (e) { problems.push('feed: invalid JSON or unreachable (' + (e.message || e) + ')'); }

  for (const p of pages) {
    try {
      const res = await get(p, { method: 'HEAD' });
      if (res.status >= 500) problems.push(`${p}: ${res.status}`);
      else if (res.status !== 200) problems.push(`${p}: ${res.status}`);
      const stage = res.headers.get('x-raven-migration-stage');
      if (stage && stage !== 'r2') warnings.push(`${p}: served from ${stage}`);
    } catch (e) { problems.push(`${p}: ${e.cause?.code || e.message}`); }
  }

  for (const c of clips) {
    try {
      const h = await get('/' + c, { method: 'HEAD' });
      if (h.status !== 200 || !String(h.headers.get('content-type')).includes('video/mp4')) problems.push(`${c}: HEAD ${h.status}`);
      if (h.headers.get('x-raven-migration-stage') !== 'r2') warnings.push(`${c}: served from ${h.headers.get('x-raven-migration-stage')}`);
      const r = await get('/' + c, { headers: { Range: 'bytes=0-15' } });
      await r.arrayBuffer();
      if (r.status !== 206 || !String(r.headers.get('content-range')).startsWith('bytes 0-15/')) problems.push(`${c}: Range ${r.status}`);
    } catch (e) { problems.push(`${c}: ${e.cause?.code || e.message}`); }
  }

  if (inventory) {
    try {
      const d = await inventory();
      if (d.missing.length) problems.push(`${d.missing.length} object(s) missing in R2: ${d.missing.slice(0, 5).join(', ')}`);
      if (d.different.length) problems.push(`R2 object differs from Git: ${d.different.slice(0, 5).join(', ')}`);
    } catch (e) { problems.push('R2 inventory failed: ' + e.message); }
  }
  return { ok: problems.length === 0, problems, warnings, checkedAt: new Date().toISOString() };
}

if (import.meta.url === `file:///${process.argv[1]?.replace(/\\/g, '/')}` || import.meta.url === `file://${process.argv[1]}`) {
  // Defaults for a local run from the release worktree: compare R2 with the last released commit (no release-lag false alarms).
  const lastFile = 'D:/CorteFlow/work/raven-cf-release-logs/last-released-sha.txt';
  const ref = process.argv[2] || (existsSync(lastFile) ? readFileSync(lastFile, 'utf8').trim() : 'origin/main');
  const tree = execFileSync('git', ['ls-tree', '-r', '--name-only', ref, '--', 'public/clips'], { encoding: 'utf8' }).trim().split('\n').filter(f => f.endsWith('.mp4'));
  const sitemap = execFileSync('git', ['show', `${ref}:public/sitemap.xml`], { encoding: 'utf8' });
  const pages = [...sitemap.matchAll(/<loc>https:\/\/ravencrow\.cloud([^<]*)<\/loc>/g)].map(m => m[1] || '/');
  let inventory = null;
  if (process.env.CLOUDFLARE_ACCOUNT_ID) {
    const { getSourceManifest, listR2All, diffManifests } = await import('./inventory.mjs');
    const token = process.env.CLOUDFLARE_API_TOKEN || JSON.parse(readFileSync(process.env.APPDATA + '/xdg.config/cloudflare/config/default.json', 'utf8')).oauth_token;
    inventory = async () => diffManifests(await getSourceManifest(ref), await listR2All({ accountId: process.env.CLOUDFLARE_ACCOUNT_ID, bucket: 'raven-crow-media', token }));
  }
  const r = await healthCheck({ pages, clips: tree.slice(-3).map(f => f.replace(/^public\//, '')), inventory });
  console.log(JSON.stringify({ ref, ...r }, null, 1));
  process.exitCode = r.ok ? 0 : 1;
}
