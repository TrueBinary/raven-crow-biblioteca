import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { releaseSite } from '../../ops/cloudflare/release.mjs';

const SHA = 'a'.repeat(40);
const okSync = { commit: SHA, uploaded: 2, updated: 1, skipped: 5, verified: 8, failed: [], planned: [{ key: 'x', size: 1 }] };
// Every dependency is injected; defaults describe a healthy release.
function deps(over = {}) {
  const calls = { sync: [] };
  const d = {
    headSha: () => SHA,
    commitExists: () => true,
    validate: () => ({ errors: [] }),
    manifest: async () => [{ key: 'index.html', size: 1, sha256: 'f' }],
    sync: async opts => (calls.sync.push(opts), okSync),
    verify: async () => ({ ok: true }),
    ...over,
  };
  return { d, calls };
}

test('healthy release syncs the pinned commit and passes health checks', async () => {
  const { d, calls } = deps();
  const r = await releaseSite({ commitSha: SHA, deps: d });
  assert.equal(r.deployedSha, SHA);
  assert.match(r.manifestSha, /^[a-f0-9]{64}$/);
  assert.equal(r.healthChecksPassed, true);
  assert.equal(calls.sync[0].gitRef, SHA);
  assert.equal(calls.sync[0].dryRun, false);
});

test('rejects malformed or unknown SHA before touching R2', async () => {
  for (const [sha, over] of [['main', {}], [SHA, { commitExists: () => false }]]) {
    const { d, calls } = deps(over);
    await assert.rejects(releaseSite({ commitSha: sha, deps: d }), /commit/);
    assert.equal(calls.sync.length, 0);
  }
});

test('checked-out HEAD differing from the pinned SHA blocks the release', async () => {
  const { d, calls } = deps({ headSha: () => 'b'.repeat(40) });
  await assert.rejects(releaseSite({ commitSha: SHA, deps: d }), /HEAD/);
  assert.equal(calls.sync.length, 0);
});

test('HEAD moving during the run is reported as failure', async () => {
  let n = 0;
  const { d } = deps({ headSha: () => (n++ === 0 ? SHA : 'c'.repeat(40)) });
  await assert.rejects(releaseSite({ commitSha: SHA, deps: d }), /HEAD changed/);
});

test('invalid site content blocks the sync', async () => {
  const { d, calls } = deps({ validate: () => ({ errors: ['editorial-feed.json: invalid JSON'] }) });
  await assert.rejects(releaseSite({ commitSha: SHA, deps: d }), /invalid JSON/);
  assert.equal(calls.sync.length, 0);
});

test('failed R2 sync fails the release', async () => {
  const { d } = deps({ sync: async () => ({ ...okSync, failed: [{ key: 'clips/a.mp4', reason: 'existing object differs' }] }) });
  await assert.rejects(releaseSite({ commitSha: SHA, deps: d }), /clips\/a\.mp4/);
});

test('failed apex health check fails the release', async () => {
  const { d } = deps({ verify: async url => ({ ok: !url.includes('//ravencrow'), status: 503 }) });
  await assert.rejects(releaseSite({ commitSha: SHA, deps: d }), /health/);
});

test('dry run never writes', async () => {
  const { d, calls } = deps();
  const r = await releaseSite({ commitSha: SHA, dryRun: true, deps: d });
  assert.equal(calls.sync[0].dryRun, true);
  assert.equal(r.healthChecksPassed, null);
});

const wf = () => readFileSync(new URL('../../.github/workflows/site-release.yml', import.meta.url), 'utf8');

test('site-release: um publicador por vez, segredos no ambiente, sem gatilho perigoso', () => {
  const y = wf();
  assert.match(y, /concurrency:\s*\n\s*group: site-release\s*\n\s*cancel-in-progress: false/);
  assert.match(y, /environment: CLoudinhoooo/);
  assert.match(y, /contents: write/);
  assert.doesNotMatch(y, /pull_request_target|^\s*token:/m);
  assert.doesNotMatch(y, /RavenNewsEngine/);
});

test('site-release: passos na ordem fotos → páginas → commit → portões → testes → push → release', () => {
  const y = wf();
  const at = s => { const i = y.indexOf(s); assert.ok(i >= 0, s); return i; };
  const order = ['import-photos.mjs', 'build-raven.py', 'build-column.py', 'build-news-index.py', 'build-library.py',
    'Atualizar paginas indexaveis da Coluna', 'content-integrity.mjs HEAD', 'public-pages.mjs HEAD',
    "node --test 'tests/cloudflare/", 'git push origin HEAD:main', 'release.mjs'];
  order.reduce((prev, s) => { const i = at(s); assert.ok(i > prev, s + ' fora de ordem'); return i; }, -1);
});

test('site-release: git add tem os mesmos caminhos do release do PC', () => {
  const ps = readFileSync(new URL('../../ops/cloudflare/release-local.ps1', import.meta.url), 'utf8');
  const paths = ps.match(/^\s*git add (index\.html[^\r\n]*)/m)[1].trim().split(/\s+/);
  const y = wf();
  for (const p of paths) assert.ok(y.includes(p), 'faltando no workflow: ' + p);
  assert.match(y, /sitemap-coluna\.xml/);
});

test('site-release: push recusado pula o release; release falha se release.mjs falhar', () => {
  const y = wf();
  const release = y.slice(y.indexOf('release.mjs') - 400);
  assert.match(release, /if: steps\.push\.outputs\.pushed == 'true'/);
  assert.match(release, /shell: bash/);
  assert.match(release, /pipefail/);
  assert.match(y, /CLOUDFLARE_API_TOKEN: \$\{\{ secrets\.CLOUDFLARE_API_TOKEN \}\}/);
  assert.match(y, /CLOUDFLARE_ACCOUNT_ID: \$\{\{ vars\.CLOUDFLARE_ACCOUNT_ID \}\}/);
  assert.match(y, /dry_run/);
});

test('workflow has no ${{ }} inside a one-line { } map or run: { } (both break YAML parsing on GitHub)', () => {
  const y = wf();
  for (const line of y.split('\n')) {
    assert.doesNotMatch(line, /:\s*\{[^}\n]*\$\{\{/, line);
    assert.doesNotMatch(line, /^\s*run:\s*\{/, line);
  }
});

test('site-release: publica a cada push na main e de hora em hora', () => {
  const y = wf();
  assert.match(y, /push:\s*\n\s*branches: \[main\]/);
  assert.match(y, /schedule:\s*\n\s*- cron: '17 \* \* \* \*'/);
  assert.match(y, /workflow_dispatch:/);
});

test('scripts de ops/cloudflare rodam como CLI também no Linux (runner do Actions)', () => {
  const dir = new URL('../../ops/cloudflare/', import.meta.url);
  for (const f of readdirSync(dir).filter((n) => n.endsWith('.mjs'))) {
    const src = readFileSync(new URL(f, dir), 'utf8');
    if (!src.includes('process.argv[1]')) continue;
    assert.ok(src.includes('import.meta.url === `file://${process.argv[1]}`'), `${f}: guarda de CLI só reconhece caminho do Windows`);
  }
});

test('site-release: push recusado só é tolerado se a main realmente andou', () => {
  const push = wf().split('- name: Push')[1].split('- name:')[0];
  assert.match(push, /git fetch -q origin main/);
  assert.match(push, /merge-base --is-ancestor origin\/main HEAD/);
  assert.match(push, /exit 1/);
});

test('site-release: Pillow com versão fixa e Resumo diz quando nada foi enviado', () => {
  const y = wf();
  assert.match(y, /pip install -q pillow==\d+\.\d+\.\d+/);
  const resumo = y.split('- name: Resumo')[1];
  assert.match(resumo, /-s release-summary\.json/);
  assert.match(resumo, /Nada enviado ao R2/);
});
