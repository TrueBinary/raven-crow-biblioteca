import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, existsSync, rmSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { importPhotos } from '../../ops/cloudflare/import-photos.mjs';

const JPG = Buffer.concat([Buffer.from([0xff, 0xd8, 0xff, 0xe0]), Buffer.alloc(200, 7)]);
const sha = b => createHash('sha256').update(b).digest('hex');

function setup({ items, credits = {}, extraFiles = {} }) {
  const root = mkdtempSync(join(tmpdir(), 'imp-'));
  const site = join(root, 'site'), drop = join(root, 'drop', '2026-11-08');
  mkdirSync(join(site, 'public', 'editorial', 'photos'), { recursive: true });
  mkdirSync(drop, { recursive: true });
  writeFileSync(join(site, 'public', 'noticias.json'), JSON.stringify({ articles: [{ id: 'nova-2026' }, { id: 'velha-2026' }] }));
  writeFileSync(join(site, 'public', 'editorial-photo-credits.json'), JSON.stringify(credits));
  writeFileSync(join(drop, 'a.jpg'), JPG);
  for (const [n, b] of Object.entries(extraFiles)) writeFileSync(join(drop, n), b);
  writeFileSync(join(drop, 'manifest.json'), JSON.stringify({ items }));
  return { root, site, dropRoot: join(root, 'drop') };
}
const ok = over => ({ file: 'a.jpg', article_id: 'nova-2026', uso_liberado: true, credit: 'Fulano/Agência Brasil', license: 'Agência Brasil: uso com crédito', source_article: 'https://agenciabrasil.ebc.com.br/x', sha256: sha(JPG), ...over });

test('imports a cleared photo with its credit', t => {
  const s = setup({ items: [ok()] }); t.after(() => rmSync(s.root, { recursive: true, force: true }));
  const r = importPhotos({ siteRoot: s.site, dropRoot: s.dropRoot });
  assert.deepEqual(r.imported, ['nova-2026']);
  assert.deepEqual(readFileSync(join(s.site, 'public/editorial/photos/nova-2026.jpg')), JPG);
  const c = JSON.parse(readFileSync(join(s.site, 'public/editorial-photo-credits.json'), 'utf8'))['nova-2026'];
  assert.deepEqual(c, { path: 'editorial/photos/nova-2026.jpg', source: 'https://agenciabrasil.ebc.com.br/x', license: 'Agência Brasil: uso com crédito', artist: 'Fulano/Agência Brasil', illustrative: false });
});

test('skips items that are not cleared or incomplete', t => {
  const s = setup({ items: [
    ok({ uso_liberado: false }),
    ok({ article_id: undefined }),
    ok({ article_id: 'nao-existe-2026' }),
    ok({ license: '' }),
    ok({ credit: '' }),
    ok({ source_article: 'http://inseguro.com/x' }),
    ok({ sha256: 'f'.repeat(64) }),
    ok({ file: '../fora.jpg' }),
    ok({ file: 'nao.jpg' }),
  ], extraFiles: { 'nao.jpg': Buffer.from('not a jpeg') } });
  t.after(() => rmSync(s.root, { recursive: true, force: true }));
  const r = importPhotos({ siteRoot: s.site, dropRoot: s.dropRoot });
  assert.deepEqual(r.imported, []);
  assert.equal(r.skipped.length, 9);
  assert.equal(existsSync(join(s.site, 'public/editorial/photos/nova-2026.jpg')), false);
});

test('never replaces a photo that is already published for the article', t => {
  const s = setup({ items: [ok({ article_id: 'velha-2026' })], credits: { 'velha-2026': { path: 'editorial/photos/velha-2026.jpg' } } });
  t.after(() => rmSync(s.root, { recursive: true, force: true }));
  const r = importPhotos({ siteRoot: s.site, dropRoot: s.dropRoot });
  assert.deepEqual(r.imported, []);
  assert.match(r.skipped[0].reason, /already has a photo/);
});

test('a broken manifest is reported, not fatal', t => {
  const s = setup({ items: [] }); t.after(() => rmSync(s.root, { recursive: true, force: true }));
  writeFileSync(join(s.dropRoot, '2026-11-08', 'manifest.json'), '{ not json');
  const r = importPhotos({ siteRoot: s.site, dropRoot: s.dropRoot });
  assert.deepEqual(r.imported, []);
  assert.match(r.skipped[0].reason, /manifest/);
});

test('accepts photos for Coluna essays (ids from coluna-ensaios.json) and keeps the caption', t => {
  const s = setup({ items: [ok({ article_id: 'ensaio-teste', caption: 'Plenário do Senado (foto de arquivo)' })] });
  t.after(() => rmSync(s.root, { recursive: true, force: true }));
  writeFileSync(join(s.site, 'public', 'coluna-ensaios.json'), JSON.stringify({ essays: [{ id: 'ensaio-teste' }] }));
  const r = importPhotos({ siteRoot: s.site, dropRoot: s.dropRoot });
  assert.deepEqual(r.imported, ['ensaio-teste']);
  const c = JSON.parse(readFileSync(join(s.site, 'public/editorial-photo-credits.json'), 'utf8'))['ensaio-teste'];
  assert.equal(c.caption, 'Plenário do Senado (foto de arquivo)');
});
