// Auditoria de indexabilidade do site no ar: lê os sitemaps e confere cada URL (status, redirect, canonical,
// noindex, hreflang recíproco). Só lê; não publica nem altera nada. Uso: node ops/seo/seo-audit.mjs [--out=arquivo.json]
const BASE = 'https://ravencrow.cloud';
const SITEMAPS = ['sitemap.xml', 'sitemap-news.xml', 'sitemap-coluna.xml'];

const attr = (tag, name) => tag.match(new RegExp(`\\b${name}\\s*=\\s*"([^"]*)"`, 'i'))?.[1];
const linkTags = html => [...html.matchAll(/<link\b[^>]*>/gi)].map(m => m[0]);

// Sinais de indexação de uma página. Puro: testável sem rede.
export function analyzePage(url, { status, location = null, html = '', xRobots = '' }) {
  const head = html.split(/<\/head>/i)[0];
  const links = linkTags(head);
  const canonicals = links.filter(t => /rel\s*=\s*"canonical"/i.test(t)).map(t => attr(t, 'href'));
  const alternates = links.filter(t => /rel\s*=\s*"alternate"/i.test(t) && attr(t, 'hreflang'))
    .map(t => ({ lang: attr(t, 'hreflang'), href: attr(t, 'href') }));
  const robots = [...head.matchAll(/<meta\b[^>]*name\s*=\s*"(?:robots|googlebot)"[^>]*>/gi)].map(m => attr(m[0], 'content') || '').join(',');
  const issues = [];
  if (status >= 300 && status < 400) issues.push(`redirect ${status} -> ${location}`);
  else if (status !== 200) issues.push(`status ${status}`);
  if (status === 200) {
    if (canonicals.length !== 1) issues.push(`canonical x${canonicals.length}`);
    else if (canonicals[0] !== url) issues.push(`canonical -> ${canonicals[0]}`);
    if (/noindex/i.test(robots + ',' + xRobots)) issues.push('noindex');
    if (/onrender\.com/i.test(head)) issues.push('referencia ao Render');
    if (/https?:\/\/www\.ravencrow\.cloud/i.test(head)) issues.push('www no <head>');
  }
  return { url, status, location, canonical: canonicals[0] || null, alternates, issues };
}

// hreflang recíproco: se A diz que B é a versão em X, B tem que citar A de volta.
export function hreflangIssues(pages) {
  const byUrl = new Map(pages.map(p => [p.url, p]));
  const out = [];
  for (const p of pages) for (const a of p.alternates) {
    if (a.href === p.url) continue;
    const q = byUrl.get(a.href);
    if (!q) continue; // fora do sitemap: o checkUrl do alvo cobre
    if (!q.alternates.some(b => b.href === p.url)) out.push(`${a.href} nao volta para ${p.url} (${a.lang})`);
  }
  return out;
}

export function sitemapLocs(xml) {
  return [...xml.matchAll(/<url>([\s\S]*?)<\/url>/g)].map(m => ({
    loc: m[1].match(/<loc>([^<]*)<\/loc>/)?.[1],
    lastmod: m[1].match(/<lastmod>([^<]*)<\/lastmod>/)?.[1] || null,
    newsDate: m[1].match(/<news:publication_date>([^<]*)</)?.[1] || null,
  }));
}

async function fetchPage(url) {
  for (let i = 0; ; i++) {
    try {
      const r = await fetch(url, { redirect: 'manual', headers: { 'user-agent': 'RavenSEOAudit/1.0' } });
      const html = r.status === 200 ? await r.text() : '';
      return { status: r.status, location: r.headers.get('location'), html, xRobots: r.headers.get('x-robots-tag') || '' };
    } catch (e) { if (i >= 2) return { status: 0, html: '', location: String(e.message) }; }
  }
}

async function pool(items, n, fn) {
  const out = new Array(items.length); let next = 0;
  await Promise.all(Array.from({ length: n }, async () => { while (next < items.length) { const i = next++; out[i] = await fn(items[i]); } }));
  return out;
}

export async function audit({ base = BASE, today = new Date().toISOString().slice(0, 10) } = {}) {
  const report = { base, at: new Date().toISOString(), sitemaps: {}, pages: [], hreflang: [], variants: [] };
  const robots = await (await fetch(base + '/robots.txt')).text();
  const all = new Map();
  for (const s of SITEMAPS) {
    const r = await fetch(`${base}/${s}`);
    const xml = await r.text();
    const locs = sitemapLocs(xml);
    const dup = locs.length - new Set(locs.map(l => l.loc)).size;
    const old = locs.filter(l => l.newsDate && (Date.parse(today) - Date.parse(l.newsDate)) / 864e5 > 2).length;
    report.sitemaps[s] = { status: r.status, urls: locs.length, duplicates: dup, inRobots: robots.includes(`${base}/${s}`), newsOlderThan2Days: s.includes('news') ? old : undefined };
    for (const l of locs) if (!all.has(l.loc)) all.set(l.loc, s);
  }
  report.pages = await pool([...all.keys()], 8, async url => ({ ...analyzePage(url, await fetchPage(url)), sitemap: all.get(url) }));
  report.hreflang = hreflangIssues(report.pages);
  // alvos de hreflang que não estão em sitemap nenhum
  const missing = [...new Set(report.pages.flatMap(p => p.alternates.map(a => a.href)).filter(h => !all.has(h)))];
  report.hreflangTargetsOutsideSitemap = await pool(missing, 8, async url => analyzePage(url, await fetchPage(url)));
  for (const v of ['http://ravencrow.cloud/', 'http://www.ravencrow.cloud/', 'https://www.ravencrow.cloud/', 'https://www.ravencrow.cloud/noticias/']) {
    const r = await fetchPage(v); report.variants.push({ url: v, status: r.status, location: r.location });
  }
  return report;
}

if (process.argv[1] && /seo-audit\.mjs$/.test(process.argv[1])) {
  const r = await audit();
  const out = process.argv.find(a => a.startsWith('--out='))?.slice(6);
  if (out) (await import('node:fs')).writeFileSync(out, JSON.stringify(r, null, 1));
  const bad = r.pages.filter(p => p.issues.length);
  const count = {};
  for (const p of bad) for (const i of p.issues) { const k = i.replace(/https?:\/\/\S+/g, 'URL'); count[k] = (count[k] || 0) + 1; }
  console.log(JSON.stringify({ sitemaps: r.sitemaps, pages: r.pages.length, withIssues: bad.length, issueKinds: count,
    hreflangProblems: r.hreflang.length, hreflangTargetsOutsideSitemap: r.hreflangTargetsOutsideSitemap.length,
    hreflangTargetsBroken: r.hreflangTargetsOutsideSitemap.filter(p => p.issues.length).map(p => p.url + ' ' + p.issues.join('; ')).slice(0, 15),
    variants: r.variants, sample: bad.slice(0, 15).map(p => `${p.url} [${p.sitemap}] ${p.issues.join('; ')}`), hreflangSample: r.hreflang.slice(0, 10) }, null, 1));
}
