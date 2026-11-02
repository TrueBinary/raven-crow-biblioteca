/* Raven Crow: AdSense ready but disabled until publisher approval. */
(() => {
  'use strict';
  const publisher = ''; // ca-pub-XXXXXXXXXXXXXXXX
  const placements = [['editorial-feed', ''], ['biblioteca', '']]; // numeric ad unit IDs
  if (!/^ca-pub-\d{16}$/.test(publisher)) return;
  const active = placements.filter(([id, slot]) => document.getElementById(id) && /^\d+$/.test(slot));
  if (!active.length) return;
  const style = document.createElement('style');
  style.textContent = '.rc-ad{max-width:1150px;margin:32px auto;padding:0 24px;clear:both}.rc-ad-label{display:block;margin:0 0 8px;color:#b5b2b0;font:11px sans-serif;text-transform:uppercase;letter-spacing:.08em}.rc-ad ins{display:block;min-height:90px}';
  document.head.append(style);
  const loader = document.createElement('script');
  loader.async = true;
  loader.crossOrigin = 'anonymous';
  loader.src = 'https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client=' + encodeURIComponent(publisher);
  document.head.append(loader);
  for (const [id, slot] of active) {
    const wrapper = document.createElement('aside');
    wrapper.className = 'rc-ad';
    wrapper.setAttribute('aria-label', 'Publicidade');
    const label = document.createElement('span');
    label.className = 'rc-ad-label';
    label.textContent = 'Publicidade';
    const ad = document.createElement('ins');
    ad.className = 'adsbygoogle';
    ad.style.display = 'block';
    ad.dataset.adClient = publisher;
    ad.dataset.adSlot = slot;
    ad.dataset.adFormat = 'auto';
    ad.dataset.fullWidthResponsive = 'true';
    wrapper.append(label, ad);
    document.getElementById(id).insertAdjacentElement('afterend', wrapper);
    (window.adsbygoogle = window.adsbygoogle || []).push({});
  }
})();