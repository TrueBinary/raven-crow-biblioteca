import test from 'node:test';
import assert from 'node:assert/strict';
import { validateSiteContent, mapSource } from '../../ops/cloudflare/content-integrity.mjs';

const article = id => ({ id, title: 'T ' + id, date: '2026-11-07', sources: [{ url: 'https://gov.br/x' }] });
// A minimal valid site; each test breaks one thing.
function site(over = {}) {
  const feed = { articles: [article('abc-2026'), article('def-2026')] };
  const files = {
    'index.html': '<html></html>',
    'public/noticias.html': '<html></html>',
    'public/coluna.html': '<html></html>',
    'public/livros.html': '<html></html>',
    'public/robots.txt': 'Sitemap: https://ravencrow.cloud/sitemap.xml',
    'public/google4d032a0e9d3268ea.html': 'google-site-verification: google4d032a0e9d3268ea.html',
    'public/editorial-feed.json': JSON.stringify(feed),
    'public/noticias.json': JSON.stringify({ articles: [] }),
    'public/editorial-images.json': JSON.stringify({ photos: { 'abc-2026': 'editorial/photos/abc-2026.jpg' }, covers: {} }),
    'public/editorial-photo-credits.json': JSON.stringify({ 'abc-2026': { license: 'CC BY 4.0', source: 'https://commons.wikimedia.org/x' } }),
    'public/editorial/photos/abc-2026.jpg': 'jpg',
    'public/noticias/abc-2026/index.html': '<html></html>',
    'public/noticias/def-2026/index.html': '<html></html>',
    'public/sitemap.xml': '<urlset><url><loc>https://ravencrow.cloud/</loc></url><url><loc>https://ravencrow.cloud/noticias/abc-2026/</loc></url><url><loc>https://ravencrow.cloud/noticias/def-2026/</loc></url></urlset>',
    ...over,
  };
  for (const [k, v] of Object.entries(files)) if (v === null) delete files[k];
  return mapSource(files);
}
const errs = s => validateSiteContent(s).errors.join('\n');

test('valid site has no errors and counts articles', () => {
  const r = validateSiteContent(site());
  assert.deepEqual(r.errors, []);
  assert.equal(r.articles, 2);
});

test('invalid JSON with escaped trailing newline is rejected', () => {
  assert.match(errs(site({ 'public/editorial-feed.json': '{"articles":[]}\\n' })), /editorial-feed\.json: invalid JSON/);
});

test('duplicate article id', () => {
  const feed = { articles: [article('abc-2026'), article('abc-2026')] };
  assert.match(errs(site({ 'public/editorial-feed.json': JSON.stringify(feed) })), /duplicate article id abc-2026/);
});

test('feed article without its HTML page', () => {
  assert.match(errs(site({ 'public/noticias/def-2026/index.html': null })), /def-2026: page public\/noticias\/def-2026\/index\.html missing/);
});

test('article without sources or with a bad date', () => {
  const feed = { articles: [{ ...article('abc-2026'), sources: [] }, { ...article('def-2026'), date: '07/11/2026' }] };
  const e = errs(site({ 'public/editorial-feed.json': JSON.stringify(feed) }));
  assert.match(e, /abc-2026: no sources/);
  assert.match(e, /def-2026: invalid date/);
});

test('photo mapped but file missing, or photo without credit', () => {
  assert.match(errs(site({ 'public/editorial/photos/abc-2026.jpg': null })), /abc-2026: image editorial\/photos\/abc-2026\.jpg missing/);
  assert.match(errs(site({ 'public/editorial-photo-credits.json': '{}' })), /abc-2026: photo without credit/);
});

test('missing column/books index or Google verification file', () => {
  assert.match(errs(site({ 'public/coluna.html': null })), /public\/coluna\.html missing/);
  assert.match(errs(site({ 'public/livros.html': null })), /public\/livros\.html missing/);
  assert.match(errs(site({ 'public/google4d032a0e9d3268ea.html': null })), /Google verification file missing/);
});

test('sitemap URL pointing at a page that does not exist', () => {
  const sm = '<urlset><url><loc>https://ravencrow.cloud/noticias/fantasma-2026/</loc></url></urlset>';
  assert.match(errs(site({ 'public/sitemap.xml': sm })), /sitemap: https:\/\/ravencrow\.cloud\/noticias\/fantasma-2026\/ has no page/);
});

test('article missing from sitemap is a warning, not a release blocker', () => {
  const sm = '<urlset><url><loc>https://ravencrow.cloud/noticias/abc-2026/</loc></url></urlset>';
  const r = validateSiteContent(site({ 'public/sitemap.xml': sm }));
  assert.deepEqual(r.errors, []);
  assert.match(r.warnings.join('\n'), /def-2026: not in sitemap/);
});
