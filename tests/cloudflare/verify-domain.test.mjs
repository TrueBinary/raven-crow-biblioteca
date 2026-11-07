import test from 'node:test';
import assert from 'node:assert/strict';
import { verifyHost } from '../../ops/cloudflare/verify-domain.mjs';

const res = (status, headers = {}) => new Response(null, { status, headers });
const fake = routes => async url => {
  const r = routes[url];
  if (r instanceof Error) throw r;
  if (!r) throw new Error('unexpected url ' + url);
  return r();
};

test('apex 503 from suspended Render fails even behind Cloudflare', async () => {
  const r = await verifyHost('https://ravencrow.cloud/', {
    fetchImpl: fake({ 'https://ravencrow.cloud/': () => res(503, { 'cf-ray': 'x', 'x-render-routing': 'suspend-by-user' }) }),
  });
  assert.equal(r.status, 503);
  assert.equal(r.cfRay, true);
  assert.equal(r.renderSuspend, true);
  assert.equal(r.ok, false);
});

test('www 200 served by the Worker passes', async () => {
  const r = await verifyHost('https://www.ravencrow.cloud/', {
    fetchImpl: fake({ 'https://www.ravencrow.cloud/': () => res(200, { 'cf-ray': 'x', 'x-raven-migration-stage': 'r2' }) }),
  });
  assert.deepEqual([r.status, r.stage, r.tlsOk, r.ok], [200, 'r2', true, true]);
});

test('200 without the Worker marker fails', async () => {
  const r = await verifyHost('https://ravencrow.cloud/', {
    fetchImpl: fake({ 'https://ravencrow.cloud/': () => res(200, { 'cf-ray': 'x' }) }),
  });
  assert.equal(r.ok, false);
});

test('http redirects to https and is followed', async () => {
  const r = await verifyHost('http://ravencrow.cloud/', {
    fetchImpl: fake({
      'http://ravencrow.cloud/': () => res(301, { location: 'https://ravencrow.cloud/' }),
      'https://ravencrow.cloud/': () => res(200, { 'cf-ray': 'x', 'x-raven-migration-stage': 'r2' }),
    }),
  });
  assert.equal(r.url, 'https://ravencrow.cloud/');
  assert.equal(r.ok, true);
});

test('redirect loop fails', async () => {
  const r = await verifyHost('https://ravencrow.cloud/', {
    fetchImpl: fake({
      'https://ravencrow.cloud/': () => res(301, { location: 'https://www.ravencrow.cloud/' }),
      'https://www.ravencrow.cloud/': () => res(301, { location: 'https://ravencrow.cloud/' }),
    }),
  });
  assert.equal(r.redirectLoop, true);
  assert.equal(r.ok, false);
});

test('TLS failure reports tlsOk=false', async () => {
  const err = Object.assign(new Error('fetch failed'), { cause: { code: 'CERT_HAS_EXPIRED' } });
  const r = await verifyHost('https://ravencrow.cloud/', { fetchImpl: fake({ 'https://ravencrow.cloud/': err }) });
  assert.deepEqual([r.status, r.tlsOk, r.ok], [0, false, false]);
});

// Live gate against production; set RAVEN_OFFLINE=1 to skip.
for (const url of ['https://ravencrow.cloud/', 'https://www.ravencrow.cloud/', 'http://ravencrow.cloud/']) {
  test('live: ' + url + ' reaches the Worker', { skip: process.env.RAVEN_OFFLINE === '1' }, async () => {
    const r = await verifyHost(url);
    assert.equal(r.ok, true, JSON.stringify(r));
  });
}
