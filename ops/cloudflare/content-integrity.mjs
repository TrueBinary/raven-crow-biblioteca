// Publication integrity gate for the Raven Crow site. Reports, never repairs: editorial data stays with its owners.
import { execFileSync } from 'node:child_process';

// Sources read repo-relative paths ('index.html', 'public/...').
export const mapSource = files => ({ exists: p => p in files, read: p => files[p] });
export function gitSource(sha, repo = process.cwd()) {
  const all = new Set(execFileSync('git', ['-C', repo, 'ls-tree', '-r', '--name-only', sha, '--', 'index.html', 'public'], { encoding: 'utf8', maxBuffer: 64 << 20 }).trim().split('\n'));
  return { exists: p => all.has(p), read: p => execFileSync('git', ['-C', repo, 'show', `${sha}:${p}`], { encoding: 'utf8', maxBuffer: 64 << 20 }) };
}

const REQUIRED = ['index.html', 'public/noticias.html', 'public/coluna.html', 'public/livros.html', 'public/robots.txt', 'public/sitemap.xml', 'public/editorial-feed.json'];
const JSON_FILES = ['public/editorial-feed.json', 'public/noticias.json', 'public/editorial-images.json', 'public/editorial-photo-credits.json', 'public/coluna-ensaios.json', 'public/livros.json'];
const ID = /^[a-z0-9-]{3,100}$/;

const pathForUrl = url => {
  const p = new URL(url).pathname;
  if (p === '/') return 'index.html';
  return 'public' + (p.endsWith('/') ? p + 'index.html' : p);
};

export function validateSiteContent(src) {
  const errors = [], warnings = [];
  for (const f of REQUIRED) if (!src.exists(f)) errors.push(f + ' missing');
  const google = ['public/google4d032a0e9d3268ea.html'];
  if (!google.some(src.exists)) errors.push('Google verification file missing');

  const json = {};
  for (const f of JSON_FILES) {
    if (!src.exists(f)) continue;
    try { json[f] = JSON.parse(src.read(f)); } catch { errors.push(f + ': invalid JSON'); }
  }

  const articles = json['public/editorial-feed.json']?.articles ?? [];
  const images = json['public/editorial-images.json'] ?? {};
  const credits = json['public/editorial-photo-credits.json'] ?? {};
  const seen = new Set();
  for (const a of articles) {
    const id = a?.id;
    if (typeof id !== 'string' || !ID.test(id)) { errors.push('article with invalid id: ' + JSON.stringify(id)); continue; }
    if (seen.has(id)) errors.push('duplicate article id ' + id);
    seen.add(id);
    if (!a.title) errors.push(id + ': no title');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(a.date || '')) errors.push(id + ': invalid date ' + JSON.stringify(a.date));
    if (!Array.isArray(a.sources) || !a.sources.length) errors.push(id + ': no sources');
    const page = `public/noticias/${id}/index.html`;
    if (!src.exists(page)) errors.push(`${id}: page ${page} missing`);
    for (const kind of ['photos', 'covers']) {
      const img = images[kind]?.[id];
      if (typeof img === 'string' && !src.exists('public/' + img)) errors.push(`${id}: image ${img} missing`);
    }
    if (typeof a.image === 'string' && a.image) {
      // Mirrors the front page's same-site check (public/raven-frontpage.js).
      const m = a.image.match(/^(?:https:\/\/(?:www\.)?ravencrow\.cloud\/)?(\/?(?:images\/|editorial\/)?[a-zA-Z0-9/_-]+\.(?:jpg|jpeg|png|webp))$/);
      if (!m || a.image.includes('..')) warnings.push(id + ': external image ignored by front page');
      else { const rel = m[1].replace(/^\//, ''); if (!src.exists('public/' + rel)) errors.push(`${id}: image ${rel} missing`); }
    }
    if (images.photos?.[id] && !credits[id]) errors.push(id + ': photo without credit');
  }

  if (src.exists('public/sitemap.xml')) {
    const locs = [...src.read('public/sitemap.xml').matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => m[1].trim());
    for (const loc of locs) {
      let path; try { path = pathForUrl(loc); } catch { errors.push('sitemap: invalid URL ' + loc); continue; }
      if (!src.exists(path)) errors.push(`sitemap: ${loc} has no page`);
    }
    const inSitemap = new Set(locs);
    for (const id of seen) if (!inSitemap.has(`https://ravencrow.cloud/noticias/${id}/`)) warnings.push(id + ': not in sitemap');
  }

  return { errors, warnings, articles: articles.length, pages: articles.length + REQUIRED.length };
}

if (import.meta.url === `file:///${process.argv[1]?.replace(/\\/g, '/')}`) {
  const sha = process.argv[2] || 'origin/main';
  const r = validateSiteContent(gitSource(sha));
  console.log(JSON.stringify({ ref: sha, ...r }, null, 1));
  process.exitCode = r.errors.length ? 1 : 0;
}
