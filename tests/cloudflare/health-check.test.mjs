import test from 'node:test';
import assert from 'node:assert/strict';
import { healthCheck } from '../../ops/cloudflare/health-check.mjs';

const CLIP = 'clips/' + 'a'.repeat(64) + '.mp4';
const feed = n => JSON.stringify({ articles: Array.from({ length: n }, (_, i) => ({ id: 'a' + i })) });
// Healthy fake site; `over` replaces responses per path.
function site(over = {}) {
  const routes = {
    '/': () => new Response('<html>', { status: 200, headers: { 'cf-ray': 'x', 'x-raven-migration-stage': 'r2' } }),
    '/editorial-feed.json': () => new Response(feed(12), { status: 200, headers: { 'cf-ray': 'x', 'x-raven-migration-stage': 'r2' } }),
    '/noticias.html': () => new Response('<html>', { status: 200, headers: { 'x-raven-migration-stage': 'r2' } }),
    ['/' + CLIP]: (init) => init?.headers?.Range
      ? new Response('x'.repeat(16), { status: 206, headers: { 'content-range': 'bytes 0-15/100', 'x-raven-migration-stage': 'r2' } })
      : new Response(null, { status: 200, headers: { 'content-type': 'video/mp4', 'x-raven-migration-stage': 'r2' } }),
    ...over,
  };
  return async (url, init) => {
    const u = new URL(url);
    const r = routes[u.pathname];
    if (r instanceof Error) throw r;
    return r ? r(init) : new Response('nf', { status: 404 });
  };
}
const deps = (over = {}, fetchOver = {}) => ({
  fetchImpl: site(fetchOver),
  pages: ['/', '/noticias.html'],
  clips: [CLIP],
  inventory: async () => ({ missing: [], different: [] }),
  ...over,
});
const problems = r => r.problems.join('\n');

test('healthy site passes', async () => {
  const r = await healthCheck(deps());
  assert.equal(r.ok, true, problems(r));
});

test('apex 503 from suspended Render is a problem', async () => {
  const r = await healthCheck(deps({}, { '/': () => new Response('', { status: 503, headers: { 'cf-ray': 'x', 'x-render-routing': 'suspend-by-user' } }) }));
  assert.equal(r.ok, false);
  assert.match(problems(r), /ravencrow\.cloud\/.*503/);
});

test('certificate error is a problem', async () => {
  const err = Object.assign(new Error('fetch failed'), { cause: { code: 'CERT_HAS_EXPIRED' } });
  const r = await healthCheck(deps({}, { '/': err }));
  assert.match(problems(r), /CERT_HAS_EXPIRED|tls/i);
});

test('malformed feed or too few articles', async () => {
  const bad = await healthCheck(deps({}, { '/editorial-feed.json': () => new Response('{"articles":[]}\\n', { status: 200, headers: { 'x-raven-migration-stage': 'r2' } }) }));
  assert.match(problems(bad), /feed.*JSON/);
  const few = await healthCheck(deps({}, { '/editorial-feed.json': () => new Response(feed(3), { status: 200, headers: { 'x-raven-migration-stage': 'r2' } }) }));
  assert.match(problems(few), /3 articles/);
});

test('missing MP4 in R2 and broken video Range', async () => {
  const r = await healthCheck(deps({ inventory: async () => ({ missing: [CLIP], different: [] }) }));
  assert.match(problems(r), /missing in R2.*clips\//);
  const nr = await healthCheck(deps({}, { ['/' + CLIP]: () => new Response(null, { status: 200, headers: { 'content-type': 'video/mp4', 'x-raven-migration-stage': 'r2' } }) }));
  assert.match(problems(nr), /Range/);
});

test('content served from GitHub fallback is flagged as a warning', async () => {
  const r = await healthCheck(deps({}, { '/noticias.html': () => new Response('<html>', { status: 200, headers: { 'x-raven-migration-stage': 'github-fallback' } }) }));
  assert.match(r.warnings.join(), /noticias\.html.*github-fallback/);
});

test('5xx on any sampled page is a problem', async () => {
  const r = await healthCheck(deps({}, { '/noticias.html': () => new Response('', { status: 502 }) }));
  assert.match(problems(r), /noticias\.html.*502/);
});

test('R2 object different from Git is a problem', async () => {
  const r = await healthCheck(deps({ inventory: async () => ({ missing: [], different: ['index.html'] }) }));
  assert.match(problems(r), /differs.*index\.html/);
});
