import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { getSourceManifest, listR2All, diffManifests, keyFor } from '../../ops/cloudflare/inventory.mjs';

const objs = (n, from = 0) => Array.from({ length: n }, (_, i) => ({ key: `k${from + i}`, size: 1, etag: 'e' }));
const page = (result, info) => () => new Response(JSON.stringify({ success: true, result, result_info: info }), { status: 200 });

test('listR2All follows cursor past a 20-object first page', async () => {
  const calls = [];
  const pages = [page(objs(20), { is_truncated: true, cursor: 'c1' }), page(objs(5, 20), { is_truncated: false })];
  const all = await listR2All({ accountId: 'a', bucket: 'b', token: 't', fetchImpl: async url => (calls.push(url), pages[calls.length - 1]()) });
  assert.equal(all.length, 25);
  assert.match(calls[0], /per_page=1000/);
  assert.doesNotMatch(calls[0], /limit=/);
  assert.match(calls[1], /cursor=c1/);
});

test('truncated page without cursor is not treated as complete', async () => {
  await assert.rejects(
    listR2All({ accountId: 'a', bucket: 'b', token: 't', fetchImpl: async () => page(objs(20), { is_truncated: true })() }),
    /truncated without a new cursor/,
  );
});

test('API failure throws instead of returning a partial list', async () => {
  await assert.rejects(listR2All({ accountId: 'a', bucket: 'b', token: 't', fetchImpl: async () => new Response('{}', { status: 403 }) }), /HTTP 403/);
});

test('diffManifests: missing, different size, matching', () => {
  const d = diffManifests(
    [{ key: 'a', size: 1 }, { key: 'b', size: 2 }, { key: 'c', size: 3 }],
    [{ key: 'b', size: 99 }, { key: 'c', size: 3 }, { key: 'extra', size: 1 }],
  );
  assert.deepEqual(d, { missing: ['a'], different: ['b'], matching: ['c'] });
});

test('keyFor strips public/ and rejects unsafe keys', () => {
  assert.equal(keyFor('index.html'), 'index.html');
  assert.equal(keyFor('public/clips/ab.mp4'), 'clips/ab.mp4');
  assert.throws(() => keyFor('public/a b.html'), /unsafe/);
  assert.throws(() => keyFor('public/../x'), /unsafe/);
  assert.throws(() => keyFor('public/__migration/import'), /unsafe/);
});

test('getSourceManifest hashes tracked index.html + public/** only', async () => {
  const dir = mkdtempSync(join(tmpdir(), 'inv-'));
  try {
    const git = (...a) => execFileSync('git', ['-C', dir, ...a], { encoding: 'utf8' });
    git('init', '-q');
    mkdirSync(join(dir, 'public', 'clips'), { recursive: true });
    writeFileSync(join(dir, 'index.html'), '<h1>x</h1>');
    writeFileSync(join(dir, 'public', 'clips', 'ab.mp4'), Buffer.from([0, 1, 2, 3]));
    writeFileSync(join(dir, 'public', '.env'), 'SECRET=1');
    writeFileSync(join(dir, 'build.py'), 'x');
    git('add', '-A');
    git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'x');
    writeFileSync(join(dir, 'public', 'untracked.txt'), 'u');
    const m = await getSourceManifest('HEAD', { repo: dir });
    assert.deepEqual(m.map(x => x.key).sort(), ['clips/ab.mp4', 'index.html']);
    const mp4 = m.find(x => x.key === 'clips/ab.mp4');
    assert.equal(mp4.size, 4);
    assert.equal(mp4.mime, 'video/mp4');
    assert.equal(mp4.sha256, createHash('sha256').update(Buffer.from([0, 1, 2, 3])).digest('hex'));
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});
