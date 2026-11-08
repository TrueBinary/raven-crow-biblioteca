/* Raven Crow: até 3 leituras relacionadas ao fim de cada matéria e de cada texto da Coluna, montadas no navegador
   a partir do editorial-feed.json e do coluna-ensaios.json. Texto novo entra sozinho; nenhuma página precisa ser regenerada. */
(function () {
  const STOP = new Set('para pela pelo pelos pelas como mais isso essa esse esta este quem qual seus suas sobre entre contra depois antes porque quando ainda essas esses estas estes outra outro outras outros sendo segundo seria podem pode nesta neste diz'.split(' '));
  const norm = s => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  const words = s => new Set(norm(s).split(/[^a-z0-9]+/).filter(w => w.length >= 4 && !/^\d+$/.test(w) && !STOP.has(w)));
  const shared = (a, b) => { let n = 0; for (const w of a) if (b.has(w)) n++; return n; };

  // notícias e textos da Coluna num formato só: {kind, id, category, title, subtitle, date, image}
  function pool(feed, column) {
    const news = (feed && Array.isArray(feed.articles) ? feed.articles : []).map(a => Object.assign({}, a, {kind: 'noticias'}));
    const essays = (column && Array.isArray(column.essays) ? column.essays : [])
      .map(e => ({kind: 'coluna', id: e.id, category: e.section || e.eyebrow, title: e.title, subtitle: e.subtitle, date: e.date, image: e.image}));
    return news.concat(essays).filter(a => a && typeof a.id === 'string' && /^[a-z0-9-]+$/.test(a.id) && a.title);
  }

  // mesma editoria vale 3, cada palavra forte em comum (id, título, subtítulo) vale 1; sem relação (< 2) não entra
  function pickRelated(current, articles, max) {
    const cat = words(current.category), text = words(current.id + ' ' + current.title + ' ' + current.subtitle);
    return articles
      .filter(a => !(a.id === current.id && (a.kind || 'noticias') === (current.kind || 'noticias')))
      .map(a => ({a, score: (shared(cat, words(a.category)) ? 3 : 0) + shared(text, words(a.id + ' ' + a.title + ' ' + a.subtitle))}))
      .filter(x => x.score >= 2)
      .sort((x, y) => y.score - x.score || String(y.a.date).localeCompare(String(x.a.date)))
      .slice(0, max)
      .map(x => x.a);
  }

  // mesma regra de imagem da capa (raven-frontpage.js): foto licenciada, senão capa SVG, senão logo
  function imagePath(a, assets) {
    const explicit = (typeof a.image === 'string' ? a.image : '').replace(/^https:\/\/(?:www\.)?ravencrow\.cloud\//, '');
    if (/^\/?(?:(?:images|editorial)\/)?[a-zA-Z0-9/_-]+\.(?:jpg|jpeg|png|webp)$/.test(explicit) && !explicit.includes('..')) return explicit.replace(/^\//, '');
    const photo = (assets.photos || {})[a.id];
    if (typeof photo === 'string' && /^editorial\/photos\/[a-z0-9-]+\.jpg$/.test(photo)) return photo;
    const cover = (assets.covers || {})[a.id];
    return typeof cover === 'string' && /^editorial\/covers\/[a-z0-9-]+\.svg$/.test(cover) ? cover : null;
  }

  if (typeof module !== 'undefined') { module.exports = {pool, pickRelated, imagePath}; return; }

  const match = location.pathname.match(/\/(noticias|coluna)\/([a-z0-9-]+)\/?$/);
  const main = document.querySelector('main');
  if (!match || !main) return;
  const base = new URL('.', document.currentScript && document.currentScript.src || location.origin + '/');
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text) e.textContent = text; return e; };
  const json = (path, opts) => fetch(new URL(path, base), opts).then(r => r.ok ? r.json() : null).catch(() => null);

  (async function () {
    const [feed, column, assets] = await Promise.all([
      json('editorial-feed.json', {cache: 'no-store'}), json('coluna-ensaios.json', {cache: 'no-store'}), json('editorial-images.json')]);
    const articles = pool(feed, column);
    const current = articles.find(a => a.kind === match[1] && a.id === match[2]);
    if (!current) return;
    // pega o dobro e só mostra o que abre de verdade: nunca link quebrado
    let candidates = pickRelated(current, articles, 6), fallback = false;
    // nada pertinente: alternativa identificada como tal ("Mais da Coluna"/"Mais notícias"), os mais recentes da mesma seção
    if (!candidates.length) {
      fallback = true;
      candidates = articles.filter(a => a.kind === current.kind && a.id !== current.id)
        .sort((x, y) => String(y.date).localeCompare(String(x.date))).slice(0, 6);
    }
    const url = a => new URL(a.kind + '/' + a.id + '/', base);
    const alive = await Promise.all(candidates.map(a => fetch(url(a), {method: 'HEAD'}).then(r => r.ok, () => false)));
    const picks = candidates.filter((_, i) => alive[i]).slice(0, 3);
    if (!picks.length) return;

    if (!document.getElementById('rc-related-style')) {
      const st = el('style'); st.id = 'rc-related-style';
      st.textContent = '.rc-related{margin:48px 0 8px;padding-top:24px;border-top:1px solid var(--stroke,#35353B)}'
        + '.rc-related h2{margin:0 0 16px}'
        + '.rc-related-grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(200px,1fr))}'
        + '.rc-related-card{display:flex;flex-direction:column;border:1px solid var(--stroke,#35353B);border-radius:12px;overflow:hidden;background:var(--surface,#18191F);color:var(--white,#F7F4ED);text-decoration:none}'
        + '.rc-related-card:hover,.rc-related-card:focus-visible{border-color:var(--accent,#E55E49)}'
        + '.rc-related-img{display:block;width:100%;height:auto;aspect-ratio:16/9;object-fit:cover;background:var(--bg,#0D0E12)}'
        + '.rc-related-img.rc-related-logo{object-fit:contain;padding:14% 36%;box-sizing:border-box}'
        + '.rc-related .rc-related-cat{display:block;margin:12px 14px 4px;color:var(--accent,#E55E49);font:700 11px/1.2 "DM Sans",sans-serif;text-transform:uppercase;letter-spacing:.12em}'
        + '.rc-related .rc-related-title{display:block;margin:0 14px 14px;color:var(--white,#F7F4ED);font:700 17px/1.3 "DM Sans",sans-serif}';
      document.head.append(st);
    }
    const box = el('section', 'rc-related');
    box.setAttribute('aria-labelledby', 'rc-related-h');
    const h = el('h2'); h.id = 'rc-related-h';
    if (!fallback) h.append('Leia ', el('em', '', 'também'));
    else if (current.kind === 'coluna') h.append('Mais da ', el('em', '', 'Coluna'));
    else h.append('Mais ', el('em', '', 'notícias'));
    const grid = el('div', 'rc-related-grid');
    const logo = new URL('raven-logo.webp', base).href;
    picks.forEach((a, i) => {
      const link = el('a', 'rc-related-card');
      link.href = url(a).pathname;
      const path = imagePath(a, assets || {});
      const img = el('img', 'rc-related-img' + (path ? '' : ' rc-related-logo'));
      img.src = path ? new URL(path, base).href : logo; img.alt = ''; img.loading = 'lazy'; img.decoding = 'async';
      img.width = 320; img.height = 180;
      img.onerror = () => { img.onerror = null; img.classList.add('rc-related-logo'); img.src = logo; };
      const label = (a.kind === 'coluna' ? 'Coluna · ' : '') + (a.category || 'Notícia');
      link.append(img, el('span', 'rc-related-cat', label), el('span', 'rc-related-title', a.title));
      link.addEventListener('click', () => {
        if (window.posthog && window.posthog.capture) window.posthog.capture('related_article_clicked',
          {source_path: location.pathname, destination_path: link.pathname, placement: 'article_end', article_id: current.id, rank: i + 1});
      });
      grid.append(link);
    });
    box.append(h, grid);
    // antes do bloco de publicidade (e do marcador de 1px dele), para o anúncio continuar sendo o último
    const ad = main.querySelector(':scope > aside[aria-label="Publicidade"]');
    const anchor = ad && ad.previousElementSibling && ad.previousElementSibling.style.height === '1px' ? ad.previousElementSibling : ad;
    if (anchor) main.insertBefore(box, anchor); else main.append(box);
    if (window.posthog && window.posthog.capture) window.posthog.capture('related_articles_shown', {article_id: current.id, count: picks.length});
  })();
})();
