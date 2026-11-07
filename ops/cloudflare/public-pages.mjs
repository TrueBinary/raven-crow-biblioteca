// SEO, analytics and ads parity for every page in the sitemap. Reports only; never edits pages.
import { gitSource } from './content-integrity.mjs';

const ORIGIN = 'https://ravencrow.cloud';
const repoPath = urlPath => (urlPath === '/' ? 'index.html' : 'public' + (urlPath.endsWith('/') ? urlPath + 'index.html' : urlPath));
const urlPathOf = file => (file === 'index.html' ? '/' : file.replace(/^public/, '').replace(/index\.html$/, ''));

export function validatePublicPages(src) {
  const errors = [], warnings = [];

  const g = 'public/google4d032a0e9d3268ea.html';
  if (!src.exists(g) || !/google-site-verification: google4d032a0e9d3268ea\.html/.test(src.read(g))) errors.push('Google verification file missing or wrong');
  if (!src.exists('public/robots.txt') || !/^Sitemap:\s*https:\/\/ravencrow\.cloud\/sitemap\.xml\s*$/m.test(src.read('public/robots.txt'))) errors.push('robots.txt does not point at https://ravencrow.cloud/sitemap.xml');
  if (!src.exists('public/ads.txt') || !/^google\.com,\s*pub-\d+,\s*DIRECT/m.test(src.read('public/ads.txt'))) errors.push('ads.txt missing publisher line');
  try {
    const ph = JSON.parse(src.read('public/raven-posthog.json'));
    if (!/^phc_\w+$/.test(ph.key || '') || !/^https:\/\//.test(ph.host || '')) throw 0;
  } catch { errors.push('PostHog config invalid (raven-posthog.json)'); }
  if (!src.exists('public/raven-analytics.js')) errors.push('raven-analytics.js missing');

  const locs = src.exists('public/sitemap.xml') ? [...src.read('public/sitemap.xml').matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1].trim()) : [];
  for (const loc of locs) {
    const path = repoPath(new URL(loc).pathname);
    if (!src.exists(path)) { errors.push(`${loc}: no page`); continue; }
    if (!path.endsWith('.html')) continue;
    const html = src.read(path);
    const canon = /<link rel="canonical" href="([^"]+)"/.exec(html)?.[1];
    if (canon !== loc) errors.push(`${loc}: canonical ${canon ?? 'missing'}`);
    const base = new URL(/<base href="([^"]+)"/.exec(html)?.[1] ?? '', ORIGIN + urlPathOf(path));
    for (const m of html.matchAll(/<link[^>]+rel="stylesheet"[^>]*>/g)) {
      const href = /href="([^"]+)"/.exec(m[0])?.[1];
      if (!href || /^(https?:)?\/\//.test(href)) continue;
      const css = repoPath(new URL(href, base).pathname);
      if (!src.exists(css)) errors.push(`${loc}: stylesheet ${css} missing`);
    }
    if (/adsbygoogle|data-ad-slot/.test(html) && !/publicidade/i.test(html)) errors.push(`${loc}: ad without label PUBLICIDADE`);
    if (!/raven-analytics\.js/.test(html)) warnings.push(`${loc}: no analytics script`);
    if (path === 'index.html' && !/"@type":\s*"WebSite"/.test(html)) errors.push('home: WebSite schema missing');
    if (/^public\/(noticias|coluna)\/[^/]+\/index\.html$/.test(path) && !/"@type":\s*"Article"/.test(html)) warnings.push(`${loc}: Article schema missing`);
  }
  return { errors, warnings, pages: locs.length };
}

if (import.meta.url === `file:///${process.argv[1]?.replace(/\\/g, '/')}`) {
  const ref = process.argv[2] || 'origin/main';
  const r = validatePublicPages(gitSource(ref));
  console.log(JSON.stringify({ ref, ...r }, null, 1));
  process.exitCode = r.errors.length ? 1 : 0;
}
