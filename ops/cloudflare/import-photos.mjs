// Imports cleared news photos dropped by the news agent (D:\RavenNewsEngine\imagens_para_claude\<date>\manifest.json)
// into the site checkout before the builders run. Only items with uso_liberado === true and full credit are taken.
import { readdirSync, readFileSync, writeFileSync, existsSync, copyFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, basename } from 'node:path';

const MAX_BYTES = 3_000_000;
const readJson = p => JSON.parse(readFileSync(p, 'utf8'));

export function importPhotos({ siteRoot, dropRoot }) {
  const imported = [], skipped = [];
  const ids = new Set();
  for (const f of ['public/noticias.json', 'public/editorial-feed.json']) {
    try { for (const a of readJson(join(siteRoot, f)).articles || []) if (a?.id) ids.add(a.id); } catch { /* file optional */ }
  }
  try { for (const e of readJson(join(siteRoot, 'public/coluna-ensaios.json')).essays || []) if (e?.id) ids.add(e.id); } catch { /* file optional */ }
  const creditsPath = join(siteRoot, 'public/editorial-photo-credits.json');
  const credits = existsSync(creditsPath) ? readJson(creditsPath) : {};

  const dirs = existsSync(dropRoot) ? readdirSync(dropRoot, { withFileTypes: true }).filter(d => d.isDirectory()).map(d => join(dropRoot, d.name)).sort() : [];
  for (const dir of dirs) {
    const mf = join(dir, 'manifest.json');
    if (!existsSync(mf)) continue;
    let items;
    try { items = readJson(mf).items || []; } catch { skipped.push({ dir, reason: 'manifest is not valid JSON' }); continue; }
    for (const it of items) {
      const skip = reason => skipped.push({ dir, file: it?.file, id: it?.article_id, reason });
      const id = it?.article_id;
      if (it?.uso_liberado !== true) { skip('uso_liberado is not true'); continue; }
      if (typeof id !== 'string' || !/^[a-z0-9-]{3,100}$/.test(id)) { skip('missing or invalid article_id'); continue; }
      if (!ids.has(id)) { skip('article_id not in noticias.json, editorial-feed.json or coluna-ensaios.json'); continue; }
      const slot = it.slot ?? 1;
      if (![1, 2, 3].includes(slot)) { skip('slot must be 1 (main photo), 2 or 3 (extra in-text photos)'); continue; }
      const key = slot === 1 ? id : `${id}--${slot}`;
      if (credits[key]) { skip('article already has a photo'); continue; }
      if (!it.license || !it.credit) { skip('license and credit are required'); continue; }
      if (!/^https:\/\//.test(it.source_article || '')) { skip('source_article must be an https URL'); continue; }
      if (typeof it.file !== 'string' || basename(it.file) !== it.file) { skip('file must be a plain name inside the batch folder'); continue; }
      const src = join(dir, it.file);
      if (!existsSync(src)) { skip('file not found'); continue; }
      const buf = readFileSync(src);
      if (buf.length > MAX_BYTES || buf[0] !== 0xff || buf[1] !== 0xd8 || buf[2] !== 0xff) { skip('not a JPEG up to 3 MB'); continue; }
      if (it.sha256 && createHash('sha256').update(buf).digest('hex') !== it.sha256) { skip('sha256 does not match manifest'); continue; }
      copyFileSync(src, join(siteRoot, 'public/editorial/photos', key + '.jpg'));
      credits[key] = { path: `editorial/photos/${key}.jpg`, source: it.source_article, license: it.license, artist: it.credit, illustrative: false, ...(it.caption ? { caption: String(it.caption) } : {}),
        ...(slot > 1 ? { placement: ['fatos', 'analise', 'contraponto'].includes(it.placement) ? it.placement : 'analise' } : {}) };
      imported.push(key);
    }
  }
  if (imported.length) writeFileSync(creditsPath, JSON.stringify(credits, null, 2) + '\n');
  return { imported, skipped };
}

if (import.meta.url === `file:///${process.argv[1]?.replace(/\\/g, '/')}`) {
  const [siteRoot, dropRoot = 'D:\\RavenNewsEngine\\imagens_para_claude'] = process.argv.slice(2);
  const r = importPhotos({ siteRoot, dropRoot });
  for (const id of r.imported) console.log('PHOTO imported ' + id);
  // Only report skips that look intended for publishing, so old review batches don't flood the log.
  for (const s of r.skipped) if (s.reason !== 'uso_liberado is not true' && s.reason !== 'article already has a photo') console.log(`PHOTO skipped ${s.file ?? ''} (${s.id ?? '-'}): ${s.reason}`);
}
