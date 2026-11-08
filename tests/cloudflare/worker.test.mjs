import test from 'node:test';
import assert from 'node:assert/strict';
import worker, { resolveKey } from '../../ops/cloudflare/raven-production-worker.mjs';

// Minimal R2 binding fake: head/get with optional {range:{offset,length}}.
function bucket(files) {
  const meta = (key, body) => ({ key, size: body.length, httpEtag: `"etag-${key}"`, writeHttpMetadata() {} });
  return {
    async head(key) { return files[key] ? meta(key, files[key]) : null; },
    async get(key, opts) {
      const b = files[key]; if (!b) return null;
      const r = opts?.range; const part = r ? b.subarray(r.offset, r.offset + r.length) : b;
      return { ...meta(key, b), body: new Blob([part]).stream() };
    },
  };
}
const MP4 = Buffer.alloc(100, 7);
const FILES = { 'index.html': Buffer.from('<h1>home</h1>'), 'noticias/abc-def/index.html': Buffer.from('<p>a</p>'), 'raven-logo.webp': Buffer.from('w'), 'raven-frontpage.js': Buffer.from('1'), 'clips/aa.mp4': MP4 };
const env = (extra = {}) => ({ RAVEN_MEDIA: bucket(FILES), ...extra });
const call = (path, init = {}, e = env()) => worker.fetch(new Request('https://ravencrow.cloud' + path, init), e);

test('root, static page and trailing-slash article come from R2', async () => {
  for (const p of ['/', '/noticias/abc-def', '/noticias/abc-def/']) {
    const r = await call(p);
    assert.equal(r.status, 200, p);
    assert.equal(r.headers.get('x-raven-migration-stage'), 'r2');
    assert.match(r.headers.get('content-type'), /text\/html/);
  }
});

test('MIME for image and JS', async () => {
  assert.equal((await call('/raven-logo.webp')).headers.get('content-type'), 'image/webp');
  assert.match((await call('/raven-frontpage.js')).headers.get('content-type'), /javascript/);
});

test('traversal, encoded traversal and migration endpoints are rejected', async () => {
  for (const p of ['/../secret', '/%2e%2e/secret', '/a/%2E%2E/b', '/a%5cb']) assert.ok([400, 404].includes((await call(p)).status), p);
  for (const m of ['GET', 'POST']) assert.equal((await call('/__migration/import', { method: m })).status, 404);
});

test('405 for disallowed methods', async () => {
  const r = await call('/', { method: 'DELETE' });
  assert.equal(r.status, 405);
  assert.equal(r.headers.get('allow'), 'GET, HEAD');
});

test('absent object is 404 and never hits GitHub when fallback is off', async t => {
  const orig = globalThis.fetch; let fetched = 0;
  globalThis.fetch = async () => { fetched++; return new Response('x'); };
  t.after(() => { globalThis.fetch = orig; });
  const r = await call('/nao-existe.html');
  assert.equal(r.status, 404);
  assert.equal(fetched, 0);
});

test('fallback only when GITHUB_FALLBACK=1, and it is labelled', async t => {
  const orig = globalThis.fetch;
  globalThis.fetch = async () => new Response('gh', { status: 200, headers: { 'Content-Length': '2' } });
  t.after(() => { globalThis.fetch = orig; });
  const r = await call('/novo.html', {}, env({ GITHUB_FALLBACK: '1' }));
  assert.equal(r.status, 200);
  assert.equal(r.headers.get('x-raven-migration-stage'), 'github-fallback');
});

test('MP4: GET 200, HEAD 200 without body, ranges 206/416', async () => {
  const get = await call('/clips/aa.mp4');
  assert.deepEqual([get.status, get.headers.get('content-length'), get.headers.get('content-type')], [200, '100', 'video/mp4']);
  assert.equal((await get.arrayBuffer()).byteLength, 100);

  const head = await call('/clips/aa.mp4', { method: 'HEAD' });
  assert.deepEqual([head.status, head.headers.get('content-length'), head.body], [200, '100', null]);

  const r1 = await call('/clips/aa.mp4', { headers: { Range: 'bytes=0-15' } });
  assert.deepEqual([r1.status, r1.headers.get('content-range'), r1.headers.get('content-length')], [206, 'bytes 0-15/100', '16']);
  assert.equal((await r1.arrayBuffer()).byteLength, 16);

  const suf = await call('/clips/aa.mp4', { headers: { Range: 'bytes=-10' } });
  assert.deepEqual([suf.status, suf.headers.get('content-range')], [206, 'bytes 90-99/100']);

  const bad = await call('/clips/aa.mp4', { headers: { Range: 'bytes=500-' } });
  assert.deepEqual([bad.status, bad.headers.get('content-range')], [416, 'bytes */100']);

  const malformed = await call('/clips/aa.mp4', { headers: { Range: 'bytes=abc' } });
  assert.equal(malformed.status, 200);
});

test('RFC 9110: invalid/multi-range ignored (200), unsatisfiable stays 416', async () => {
  for (const v of ['bytes=abc', 'items=0-1', 'bytes=0-1,4-5']) { const r = await call('/clips/aa.mp4', { headers: { Range: v } }); assert.deepEqual([r.status, (await r.arrayBuffer()).byteLength], [200, 100], v); }
  const z = await call('/clips/aa.mp4', { headers: { Range: 'bytes=-0' } });
  assert.deepEqual([z.status, z.headers.get('content-range')], [416, 'bytes */100']);
});

test('If-None-Match: *, lists and weak tags match; 304 carries ETag and Cache-Control', async () => {
  for (const v of ['*', '"x", "etag-clips/aa.mp4"', 'W/"etag-clips/aa.mp4"']) {
    const r = await call('/clips/aa.mp4', { headers: { 'If-None-Match': v } });
    assert.deepEqual([r.status, r.headers.get('etag'), r.headers.get('cache-control')], [304, '"etag-clips/aa.mp4"', 'public, max-age=300'], v);
  }
  assert.equal((await call('/clips/aa.mp4', { headers: { 'If-None-Match': '"nope"' } })).status, 200);
});

test('migration health reports production', async () => {
  assert.deepEqual(await (await call('/__raven_migration_health')).json(), { status: 'production', R2: true, domainCutover: true, githubFallback: false });
  assert.equal((await (await call('/__raven_migration_health', {}, env({ GITHUB_FALLBACK: '1' }))).json()).githubFallback, true);
});

test('ETag match returns 304', async () => {
  const r = await call('/clips/aa.mp4', { headers: { 'If-None-Match': '"etag-clips/aa.mp4"' } });
  assert.equal(r.status, 304);
});

test('hash-named clips are immutable; HTML/JSON stay short-lived', async () => {
  assert.equal((await call('/clips/aa.mp4')).headers.get('cache-control'), 'public, max-age=300');
  const sha = 'b'.repeat(64);
  const e = { RAVEN_MEDIA: bucket({ ...FILES, [`clips/${sha}.mp4`]: MP4, [`clips/${sha}.jpg`]: Buffer.from('j') }) };
  for (const ext of ['mp4', 'jpg']) assert.equal((await call(`/clips/${sha}.${ext}`, {}, e)).headers.get('cache-control'), 'public, max-age=31536000, immutable');
  assert.equal((await call('/')).headers.get('cache-control'), 'public, max-age=60');
});

test('HTML pages get the social bar script just before </body>; other files untouched', async () => {
  const e = env({ RAVEN_MEDIA: bucket({ ...FILES, 'index.html': Buffer.from('<html><body><h1>home</h1></body></html>') }) });
  const r = await call('/', {}, e);
  const html = await r.text();
  assert.match(html, /<h1>home<\/h1><script data-cfasync="false" src="https:\/\/bauval\.org\/14\/4615ad4de14cf536c88fee7d3ea00470"><\/script><div class="gtranslate_wrapper"><\/div>.*cdn\.gtranslate\.net\/widgets\/latest\/float\.js" defer><\/script><\/body>/);
  assert.equal(r.headers.get('content-length'), String(Buffer.byteLength(html)));
  assert.equal(await (await call('/raven-frontpage.js', {}, e)).text(), '1');
});

test('translated editions: /en, /es and /<lang>/noticias/<id> map to their index.html', () => {
  assert.equal(resolveKey('/en'), 'en/index.html');
  assert.equal(resolveKey('/es/'), 'es/index.html');
  assert.equal(resolveKey('/en/noticias/abc-def'), 'en/noticias/abc-def/index.html');
  assert.equal(resolveKey('/es/noticias/abc-def/'), 'es/noticias/abc-def/index.html');
  assert.equal(resolveKey('/fr/noticias/abc-def'), 'fr/noticias/abc-def');
});

test('every HTML page gets the same favicon links in <head>, unless it already declares one', async () => {
  const e = env({ RAVEN_MEDIA: bucket({ ...FILES, 'index.html': Buffer.from('<html><head><title>x</title></head><body>a</body></html>'), 'noticias/abc-def/index.html': Buffer.from('<html><head><link rel="icon" href="x.ico"></head><body>b</body></html>') }) });
  const home = await (await call('/', {}, e)).text();
  assert.match(home, /<link rel="icon" href="\/favicon\.ico" sizes="48x48">.*<link rel="apple-touch-icon" href="\/apple-touch-icon\.png"><\/head>/);
  const art = await (await call('/noticias/abc-def/', {}, e)).text();
  assert.equal((art.match(/rel="icon"/g) || []).length, 1);
});
