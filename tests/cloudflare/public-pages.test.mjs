import test from 'node:test';
import assert from 'node:assert/strict';
import { mapSource } from '../../ops/cloudflare/content-integrity.mjs';
import { validatePublicPages } from '../../ops/cloudflare/public-pages.mjs';

const head = (canon, extra = '') => `<html><head><link rel="canonical" href="${canon}"><link rel="stylesheet" href="raven-unified.css">${extra}</head><body><script src="raven-analytics.js"></script></body></html>`;
const ld = t => `<script type="application/ld+json">{"@type": "${t}", "datePublished": "2026-11-07"}</script>`;
function site(over = {}) {
  const files = {
    'index.html': head('https://ravencrow.cloud/', ld('WebSite')) + '<ins class="adsbygoogle"></ins><span>PUBLICIDADE</span>',
    'public/raven-unified.css': 'body{}',
    'public/noticias/abc-2026/index.html': head('https://ravencrow.cloud/noticias/abc-2026/', ld('Article')).replace('raven-unified.css', '../../raven-unified.css'),
    'public/sitemap.xml': '<urlset><url><loc>https://ravencrow.cloud/</loc></url><url><loc>https://ravencrow.cloud/noticias/abc-2026/</loc></url></urlset>',
    'public/robots.txt': 'User-agent: *\nAllow: /\nSitemap: https://ravencrow.cloud/sitemap.xml',
    'public/google4d032a0e9d3268ea.html': 'google-site-verification: google4d032a0e9d3268ea.html',
    'public/raven-posthog.json': '{"key":"phc_abc","host":"https://us.i.posthog.com"}',
    'public/raven-analytics.js': '//',
    'public/ads.txt': 'google.com, pub-9229550453313503, DIRECT, f08c47fec0942fa0',
    ...over,
  };
  for (const [k, v] of Object.entries(files)) if (v === null) delete files[k];
  return mapSource(files);
}
const run = s => validatePublicPages(s);

test('parity site passes', () => {
  const r = run(site());
  assert.deepEqual(r.errors, []);
  assert.deepEqual(r.warnings, []);
});

test('sitemap page that does not exist', () => {
  const sm = '<urlset><url><loc>https://ravencrow.cloud/noticias/nada-2026/</loc></url></urlset>';
  assert.match(run(site({ 'public/sitemap.xml': sm })).errors.join(), /nada-2026.*no page/);
});

test('canonical not matching the apex sitemap URL', () => {
  const page = head('https://www.ravencrow.cloud/noticias/abc-2026/', ld('Article'));
  assert.match(run(site({ 'public/noticias/abc-2026/index.html': page })).errors.join(), /abc-2026.*canonical/);
});

test('home without WebSite schema, article without Article schema', () => {
  assert.match(run(site({ 'index.html': head('https://ravencrow.cloud/') })).errors.join(), /WebSite/);
  const art = head('https://ravencrow.cloud/noticias/abc-2026/');
  assert.match(run(site({ 'public/noticias/abc-2026/index.html': art })).warnings.join(), /abc-2026.*Article/);
});

test('missing or wrong Google verification file', () => {
  assert.match(run(site({ 'public/google4d032a0e9d3268ea.html': null })).errors.join(), /Google verification/);
  assert.match(run(site({ 'public/google4d032a0e9d3268ea.html': '<html></html>' })).errors.join(), /Google verification/);
});

test('broken PostHog config, and a page without analytics', () => {
  assert.match(run(site({ 'public/raven-posthog.json': '{"key":"","host":"http://x"}' })).errors.join(), /PostHog/);
  const noAnalytics = head('https://ravencrow.cloud/noticias/abc-2026/', ld('Article')).replace('<script src="raven-analytics.js"></script>', '');
  assert.match(run(site({ 'public/noticias/abc-2026/index.html': noAnalytics })).warnings.join(), /abc-2026.*analytics/);
});

test('stylesheet that does not exist is blocking', () => {
  assert.match(run(site({ 'public/raven-unified.css': null })).errors.join(), /raven-unified\.css missing/);
});

test('ad slot without PUBLICIDADE label, or ads.txt without publisher', () => {
  assert.match(run(site({ 'index.html': head('https://ravencrow.cloud/', ld('WebSite')) + '<ins class="adsbygoogle"></ins>' })).errors.join(), /ad without label/);
  assert.match(run(site({ 'public/ads.txt': '' })).errors.join(), /ads\.txt/);
});

test('robots.txt must point at the apex sitemap', () => {
  assert.match(run(site({ 'public/robots.txt': 'User-agent: *\nDisallow: /' })).errors.join(), /robots/);
});

test('stylesheets resolve against <base href> like the browser does', () => {
  const page = head('https://ravencrow.cloud/noticias/abc-2026/', '<base href="../../">' + ld('Article'));
  assert.deepEqual(run(site({ 'public/noticias/abc-2026/index.html': page })).errors, []);
});
