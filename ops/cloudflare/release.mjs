// Gated GitHub main -> R2 release: pinned SHA, content checks, delete-free sync, live health checks.
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { getSourceManifest } from './inventory.mjs';
import { syncMedia } from './r2-sync.mjs';
import { verifyHost } from './verify-domain.mjs';
import { validateSiteContent, gitSource } from './content-integrity.mjs';
import { validatePublicPages } from './public-pages.mjs';

const git = (...a) => execFileSync('git', a, { encoding: 'utf8', maxBuffer: 64 << 20 }).trim();
const HOSTS = ['https://ravencrow.cloud/', 'https://www.ravencrow.cloud/', 'https://ravencrow.cloud/editorial-feed.json'];

// Structural publish gate; editorial integrity lives in content-integrity.mjs.
export function validateCommit(sha) {
  const errors = [];
  const files = new Set(git('ls-tree', '-r', '--name-only', sha, '--', 'index.html', 'public').split('\n'));
  for (const f of ['index.html', 'public/editorial-feed.json', 'public/noticias.json', 'public/sitemap.xml']) if (!files.has(f)) errors.push(f + ': missing');
  for (const f of ['public/editorial-feed.json', 'public/noticias.json', 'public/editorial-images.json']) {
    if (!files.has(f)) continue;
    try { JSON.parse(git('show', `${sha}:${f}`)); } catch { errors.push(f + ': invalid JSON'); }
  }
  if (!/<html/i.test(git('show', `${sha}:index.html`))) errors.push('index.html: not HTML');
  return { errors };
}

const defaults = {
  headSha: () => git('rev-parse', 'HEAD'),
  commitExists: sha => { try { git('cat-file', '-e', sha + '^{commit}'); return true; } catch { return false; } },
  validate: sha => {
    const src = gitSource(sha), base = validateCommit(sha), content = validateSiteContent(src), pages = validatePublicPages(src);
    return { errors: [...base.errors, ...content.errors, ...pages.errors], warnings: [...content.warnings, ...pages.warnings] };
  },
  manifest: sha => getSourceManifest(sha),
  sync: opts => syncMedia(opts),
  verify: url => verifyHost(url, { expectedMarker: 'r2' }),
};

export async function releaseSite({ commitSha, dryRun = false, deps = {}, log = () => {} }) {
  const d = { ...defaults, ...deps };
  if (!/^[a-f0-9]{40}$/.test(commitSha || '') || !d.commitExists(commitSha)) throw Error('unknown commit: ' + commitSha);
  if (d.headSha() !== commitSha) throw Error('checked-out HEAD is not the pinned commit');

  const { errors, warnings = [] } = d.validate(commitSha);
  if (errors.length) throw Error('content validation failed: ' + errors.join('; '));
  for (const w of warnings) log('warning: ' + w);

  const manifest = await d.manifest(commitSha);
  const manifestSha = createHash('sha256').update(JSON.stringify(manifest.map(m => [m.key, m.size, m.sha256]).sort())).digest('hex');

  const sync = await d.sync({ gitRef: commitSha, dryRun });
  if (sync.failed.length) throw Error('R2 sync failed: ' + sync.failed.map(f => `${f.key} (${f.reason})`).join(', '));
  if (d.headSha() !== commitSha) throw Error('HEAD changed during release');
  log(`sync ${dryRun ? 'planned' : 'done'}: uploaded ${sync.uploaded}, updated ${sync.updated ?? 0}, skipped ${sync.skipped}, planned ${sync.planned.length}`);
  if (dryRun) return { deployedSha: commitSha, manifestSha, healthChecksPassed: null, sync };

  const health = await Promise.all(HOSTS.map(async u => ({ url: u, ...(await d.verify(u)) })));
  const bad = health.filter(h => !h.ok);
  if (bad.length) throw Error('health check failed: ' + bad.map(h => `${h.url} ${h.status}`).join(', '));
  return { deployedSha: commitSha, manifestSha, healthChecksPassed: true, sync };
}

if (import.meta.url === `file:///${process.argv[1]?.replace(/\\/g, '/')}` || import.meta.url === `file://${process.argv[1]}`) {
  const args = process.argv.slice(2);
  const commitSha = args.find(a => !a.startsWith('--')) || git('rev-parse', 'HEAD');
  try {
    const r = await releaseSite({ commitSha, dryRun: args.includes('--dry-run'), log: m => console.error(m) });
    const { sync, ...summary } = r;
    console.log(JSON.stringify({ ...summary, uploaded: sync.uploaded, updated: sync.updated, skipped: sync.skipped, changed: sync.planned.map(p => p.key) }, null, 1));
  } catch (e) {
    console.error('RELEASE BLOCKED: ' + e.message);
    process.exitCode = 1;
  }
}
