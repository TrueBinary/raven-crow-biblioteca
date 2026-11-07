import test from 'node:test';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { verifyPublishedVideo, findDuplicateClips } from '../../ops/cloudflare/video-url.mjs';

const BODY = Buffer.alloc(64, 3);
const SHA = createHash('sha256').update(BODY).digest('hex');
const URL_OK = `https://ravencrow.cloud/clips/${SHA}.mp4`;

// Fake origin: serves BODY with Range support; options break one property at a time.
function origin({ stage = 'r2', body = BODY, range = true, status = 200, mime = 'video/mp4' } = {}) {
  return async (url, init = {}) => {
    if (status !== 200) return new Response(null, { status });
    const h = { 'content-type': mime, 'x-raven-migration-stage': stage, 'accept-ranges': 'bytes' };
    const r = init.headers?.Range;
    if (r && range) {
      const [a, b] = r.replace('bytes=', '').split('-').map(Number);
      const part = body.subarray(a, b + 1);
      return new Response(init.method === 'HEAD' ? null : part, { status: 206, headers: { ...h, 'content-range': `bytes ${a}-${a + part.length - 1}/${body.length}`, 'content-length': String(part.length) } });
    }
    return new Response(init.method === 'HEAD' ? null : body, { status: 200, headers: { ...h, 'content-length': String(body.length) } });
  };
}

test('video on R2 with matching bytes, hash and ranges is ready', async () => {
  const r = await verifyPublishedVideo(URL_OK, SHA, BODY.length, { fetchImpl: origin() });
  assert.deepEqual([r.ok, r.headStatus, r.rangeStatus, r.mime], [true, 200, 206, 'video/mp4']);
});

test('served by GitHub fallback (not yet on R2) is not ready', async () => {
  const r = await verifyPublishedVideo(URL_OK, SHA, BODY.length, { fetchImpl: origin({ stage: 'github-fallback' }) });
  assert.equal(r.ok, false);
  assert.match(r.reason, /not served from R2/);
});

test('future file not uploaded yet (404) is not ready', async () => {
  const r = await verifyPublishedVideo(URL_OK, SHA, BODY.length, { fetchImpl: origin({ status: 404 }) });
  assert.deepEqual([r.ok, r.headStatus], [false, 404]);
});

test('wrong byte count or wrong content hash is not ready', async () => {
  assert.match((await verifyPublishedVideo(URL_OK, SHA, 999, { fetchImpl: origin() })).reason, /size/);
  const other = Buffer.alloc(64, 9);
  assert.match((await verifyPublishedVideo(URL_OK, SHA, 64, { fetchImpl: origin({ body: other }) })).reason, /sha256/);
});

test('missing Range support is not ready', async () => {
  const r = await verifyPublishedVideo(URL_OK, SHA, BODY.length, { fetchImpl: origin({ range: false }) });
  assert.equal(r.ok, false);
  assert.match(r.reason, /range/i);
});

test('URL must be the canonical hash-named clip path', async () => {
  for (const u of [`https://evil.example/clips/${SHA}.mp4`, `https://ravencrow.cloud/clips/${'0'.repeat(64)}.mp4`, `http://ravencrow.cloud/clips/${SHA}.mp4`]) {
    const r = await verifyPublishedVideo(u, SHA, BODY.length, { fetchImpl: origin() });
    assert.equal(r.ok, false, u);
  }
});

test('duplicate clip hashes in a queue are reported', () => {
  const q = [{ id: 'a', url: URL_OK }, { id: 'b', url: URL_OK }, { id: 'c', url: `https://ravencrow.cloud/clips/${'1'.repeat(64)}.mp4` }];
  assert.deepEqual(findDuplicateClips(q), [{ sha: SHA, ids: ['a', 'b'] }]);
});

test('www host used by the Buffer handoff is accepted', async () => {
  const r = await verifyPublishedVideo(`https://www.ravencrow.cloud/clips/${SHA}.mp4`, SHA, BODY.length, { fetchImpl: origin() });
  assert.equal(r.ok, true, r.reason);
});
