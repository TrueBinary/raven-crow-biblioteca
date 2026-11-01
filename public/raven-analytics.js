/* Raven Crow: PostHog website events, configured via public JSON (project token is public). */
(async function () {
  let cfg;
  try {
    const configUrl = document.currentScript?.src
      ? new URL('raven-posthog.json', document.currentScript.src)
      : new URL('/raven-posthog.json', location.href);
    const response = await fetch(configUrl);
    if (!response.ok) return;
    cfg = await response.json();
  } catch (_) { return; }
  if (!cfg || !/^phc_[a-zA-Z0-9]+$/.test(cfg.key) || !/^https:\/\/[a-z0-9.-]+$/i.test(cfg.host)) return;
  const ph = window.posthog = window.posthog || [];
  ph._i = ph._i || [];
  for (const method of ['capture','identify','reset','register','opt_out_capturing','opt_in_capturing']) {
    ph[method] = function(...args) { ph.push([method, ...args]); };
  }
  ph.init = function(key, options) { ph._i.push([key, options, 'posthog']); };
  ph.__SV = 1;
  ph.init(cfg.key, {api_host:cfg.host, autocapture:false, capture_pageview:true,
    person_profiles:'identified_only', disable_session_recording:true});
  const script = document.createElement('script');
  script.src = cfg.host.replace('.i.posthog.com','-assets.i.posthog.com') + '/static/array.js';
  script.async = true;
  document.head.appendChild(script);
  document.addEventListener('click', function(e) {
    const link = e.target.closest('a[href]');
    if (!link) return;
    const url = new URL(link.href, location.href);
    const kind = link.dataset.track || (url.hostname === 'pixgg.com' ? 'pix' :
      url.hostname.endsWith('amazon.com.br') ? 'book' : null);
    if (!kind || !window.posthog?.capture) return;
    window.posthog.capture(kind === 'pix' ? 'pix_clicked' : kind === 'book' ? 'book_clicked' : 'library_clicked',
      {placement:link.dataset.placement || location.pathname, destination_host:url.hostname,
       book_id:link.closest('[data-id]')?.dataset.id || null});
  });
})();
