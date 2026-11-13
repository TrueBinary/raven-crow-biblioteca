import test from 'node:test';
import assert from 'node:assert/strict';
import { analyzePage, hreflangIssues, sitemapLocs } from '../../ops/seo/seo-audit.mjs';

const page = (canon, extra = '') => `<html><head><link rel="canonical" href="${canon}">${extra}</head><body></body></html>`;

test('página saudável não tem problemas', () => {
  const u = 'https://ravencrow.cloud/noticias/a/';
  assert.deepEqual(analyzePage(u, { status: 200, html: page(u) }).issues, []);
});

test('canonical apontando para outra URL, noindex, Render e www viram problemas', () => {
  const u = 'https://ravencrow.cloud/noticias/a/';
  const r = analyzePage(u, { status: 200, html: page('https://raven.onrender.com/a/', '<meta name="robots" content="noindex"><link rel="alternate" hreflang="en" href="https://www.ravencrow.cloud/en/a/">') });
  assert.ok(r.issues.includes('canonical -> https://raven.onrender.com/a/'));
  assert.ok(r.issues.includes('noindex'));
  assert.ok(r.issues.includes('referencia ao Render'));
  assert.ok(r.issues.includes('www no <head>'));
});

test('URL do sitemap que redireciona ou some é problema', () => {
  assert.deepEqual(analyzePage('https://ravencrow.cloud/x', { status: 301, location: '/x/' }).issues, ['redirect 301 -> /x/']);
  assert.deepEqual(analyzePage('https://ravencrow.cloud/y', { status: 404 }).issues, ['status 404']);
});

test('canonical duplicado é problema; canonical no body não conta', () => {
  const u = 'https://ravencrow.cloud/a';
  assert.deepEqual(analyzePage(u, { status: 200, html: page(u, `<link rel="canonical" href="${u}">`) }).issues, ['canonical x2']);
  assert.deepEqual(analyzePage(u, { status: 200, html: page(u) + `<link rel="canonical" href="https://x/">` }).issues, []);
});

test('hreflang sem volta é detectado', () => {
  const pt = { url: 'https://r/pt/', alternates: [{ lang: 'en', href: 'https://r/en/' }] };
  const en = { url: 'https://r/en/', alternates: [] };
  assert.deepEqual(hreflangIssues([pt, en]), ['https://r/en/ nao volta para https://r/pt/ (en)']);
  en.alternates.push({ lang: 'pt-BR', href: 'https://r/pt/' });
  assert.deepEqual(hreflangIssues([pt, en]), []);
});

test('sitemapLocs lê loc, lastmod e data de notícia', () => {
  const xml = '<urlset><url><loc>https://r/a</loc><lastmod>2026-11-12</lastmod></url><url><loc>https://r/b</loc><news:news><news:publication_date>2026-11-10</news:publication_date></news:news></url></urlset>';
  assert.deepEqual(sitemapLocs(xml), [{ loc: 'https://r/a', lastmod: '2026-11-12', newsDate: null }, { loc: 'https://r/b', lastmod: null, newsDate: '2026-11-10' }]);
});
