import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { syncMedia } from '../../ops/cloudflare/r2-sync.mjs';

const md5 = b => createHash('md5').update(b).digest('hex');
const FILES = { 'index.html': Buffer.from('<h1>x</h1>'), 'public/a.txt': Buffer.from('aaa'), 'public/clips/ab.mp4': Buffer.from([0, 1, 2, 3, 4]) };

function repo() {
  const dir = mkdtempSync(join(tmpdir(), 'r2s-'));
  const git = (...a) => execFileSync('git', ['-C', dir, ...a], { encoding: 'utf8' });
  git('init', '-q');
  for (const [p, b] of Object.entries(FILES)) { mkdirSync(join(dir, p, '..'), { recursive: true }); writeFileSync(join(dir, p), b); }
  git('add', '-A');
  git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'x');
  return dir;
}

// Fake R2: objects map key -> Buffer; no delete capability on purpose.
function fakeApi(initial = {}, { failOnce = new Set(), corrupt = new Set() } = {}) {
  const objects = new Map(Object.entries(initial));
  const puts = [];
  return {
    objects, puts,
    async list() { return [...objects].map(([key, b]) => ({ key, size: b.length, etag: md5(b) })); },
    async put(key, body) {
      puts.push(key);
      if (failOnce.delete(key)) { const e = Error('HTTP 503'); e.status = 503; throw e; }
      const stored = corrupt.has(key) ? Buffer.concat([body, Buffer.from('!')]) : body;
      objects.set(key, stored);
      return { key, size: stored.length, etag: md5(stored) };
    },
  };
}

test('uploads missing objects, skips existing identical ones, preserves hash-named mp4 key', async t => {
  const dir = repo(); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const api = fakeApi({ 'a.txt': FILES['public/a.txt'] });
  const r = await syncMedia({ gitRef: 'HEAD', repo: dir, api });
  assert.deepEqual([r.uploaded, r.skipped, r.verified, r.failed.length], [2, 1, 3, 0]);
  assert.deepEqual(api.puts.sort(), ['clips/ab.mp4', 'index.html']);
  assert.deepEqual(api.objects.get('clips/ab.mp4'), FILES['public/clips/ab.mp4']);
});

test('same key with different size or content stops everything, no overwrite', async t => {
  const dir = repo(); t.after(() => rmSync(dir, { recursive: true, force: true }));
  for (const bad of [Buffer.from('zz'), Buffer.from([9, 9, 9, 9, 9])]) {
    const api = fakeApi({ 'clips/ab.mp4': bad });
    const r = await syncMedia({ gitRef: 'HEAD', repo: dir, api });
    assert.equal(r.uploaded, 0);
    assert.deepEqual(api.puts, []);
    assert.deepEqual(r.failed.map(f => f.key), ['clips/ab.mp4']);
    assert.match(r.failed[0].reason, /differs/);
  }
});

test('transient failure is retried without a duplicate completed upload', async t => {
  const dir = repo(); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const api = fakeApi({}, { failOnce: new Set(['clips/ab.mp4']) });
  const r = await syncMedia({ gitRef: 'HEAD', repo: dir, api, retryDelayMs: 1 });
  assert.equal(r.failed.length, 0);
  assert.equal(api.puts.filter(k => k === 'clips/ab.mp4').length, 2);
  assert.equal(r.uploaded, 3);
});

test('upload whose stored bytes do not match is reported failed', async t => {
  const dir = repo(); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const api = fakeApi({}, { corrupt: new Set(['index.html']) });
  const r = await syncMedia({ gitRef: 'HEAD', repo: dir, api });
  assert.deepEqual(r.failed.map(f => f.key), ['index.html']);
  assert.match(r.failed[0].reason, /verify/);
});

test('dry run writes nothing; rerun after interruption only uploads the rest', async t => {
  const dir = repo(); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const api = fakeApi();
  const dry = await syncMedia({ gitRef: 'HEAD', repo: dir, api, dryRun: true });
  assert.deepEqual(api.puts, []);
  assert.equal(dry.planned.length, 3);
  api.objects.set('index.html', FILES['index.html']); // simulates a run interrupted after one upload
  const r = await syncMedia({ gitRef: 'HEAD', repo: dir, api });
  assert.deepEqual(api.puts.sort(), ['a.txt', 'clips/ab.mp4']);
  assert.equal(r.skipped, 1);
});

test('extra objects in R2 are never deleted', async t => {
  const dir = repo(); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const api = fakeApi({ 'old/legacy.mp4': Buffer.from('old') });
  await syncMedia({ gitRef: 'HEAD', repo: dir, api });
  assert.ok(api.objects.has('old/legacy.mp4'));
});

test('site text files are updated in place; media with the same key still blocks', async t => {
  const dir = repo(); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const api = fakeApi({ 'index.html': Buffer.from('<h1>old</h1>'), 'a.txt': FILES['public/a.txt'], 'clips/ab.mp4': FILES['public/clips/ab.mp4'] });
  const r = await syncMedia({ gitRef: 'HEAD', repo: dir, api });
  assert.equal(r.failed.length, 0);
  assert.equal(r.updated, 1);
  assert.deepEqual(api.objects.get('index.html'), FILES['index.html']);

  const api2 = fakeApi({ 'clips/ab.mp4': Buffer.from([9, 9, 9, 9, 9]) });
  const r2 = await syncMedia({ gitRef: 'HEAD', repo: dir, api: api2 });
  assert.deepEqual(r2.failed.map(f => f.key), ['clips/ab.mp4']);
  assert.deepEqual(api2.puts, []);
});

function repoWith(files) {
  const dir = mkdtempSync(join(tmpdir(), 'r2o-'));
  const git = (...a) => execFileSync('git', ['-C', dir, ...a], { encoding: 'utf8' });
  git('init', '-q');
  for (const [p, b] of Object.entries(files)) { mkdirSync(join(dir, p, '..'), { recursive: true }); writeFileSync(join(dir, p), b); }
  git('add', '-A');
  git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'x');
  return dir;
}
const NEW_ARTICLE = {
  'index.html': '<h1>home</h1>',
  'public/editorial-feed.json': '{"articles":[{"id":"nova-2026"}]}',
  'public/sitemap.xml': '<urlset/>',
  'public/noticias/nova-2026/index.html': '<p>nova</p>',
  'public/editorial/photos/nova-2026.jpg': 'jpg',
  ['public/clips/' + 'c'.repeat(64) + '.mp4']: 'mp4',
};

test('uploads media first, then new pages, and entry files (home, feed, sitemap) last', async t => {
  const dir = repoWith(NEW_ARTICLE); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const api = fakeApi();
  const r = await syncMedia({ gitRef: 'HEAD', repo: dir, api, maxConcurrency: 4 });
  assert.equal(r.failed.length, 0);
  const pos = k => api.puts.indexOf(k);
  for (const media of ['editorial/photos/nova-2026.jpg', 'clips/' + 'c'.repeat(64) + '.mp4']) assert.ok(pos(media) < pos('noticias/nova-2026/index.html'), media);
  for (const entry of ['index.html', 'editorial-feed.json', 'sitemap.xml']) assert.ok(pos('noticias/nova-2026/index.html') < pos(entry), entry);
});

test('a failed phase stops later phases, so the feed never links to a missing page', async t => {
  const dir = repoWith(NEW_ARTICLE); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const api = fakeApi();
  const put = api.put;
  api.put = async (k, b, m) => { if (k === 'noticias/nova-2026/index.html') { const e = Error('HTTP 400'); e.status = 400; throw e; } return put(k, b, m); };
  const r = await syncMedia({ gitRef: 'HEAD', repo: dir, api });
  assert.deepEqual(r.failed.map(f => f.key), ['noticias/nova-2026/index.html']);
  for (const entry of ['index.html', 'editorial-feed.json', 'sitemap.xml']) assert.equal(api.objects.has(entry), false, entry);
});

test('token file being rewritten by the cf CLI is retried, not a failed release', async t => {
  const { readTokenFile } = await import('../../ops/cloudflare/r2-sync.mjs');
  const { spawn } = await import('node:child_process');
  const dir = mkdtempSync(join(tmpdir(), 'tok-')); t.after(() => rmSync(dir, { recursive: true, force: true }));
  const f = join(dir, 'default.json');
  // The reader is synchronous, so the late write must come from another process.
  spawn(process.execPath, ['-e', `setTimeout(()=>require('fs').writeFileSync(${JSON.stringify(f)},JSON.stringify({oauth_token:'abc'})),300)`], { stdio: 'ignore' });
  assert.equal(readTokenFile(f, { tries: 30, waitMs: 100 }), 'abc');
  assert.throws(() => readTokenFile(join(dir, 'never.json'), { tries: 2, waitMs: 10 }), /ENOENT/);
});
