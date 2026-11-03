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
  // PostHog official HTML snippet bootstrap. Required methods must be stubbed before array.js loads.
  !function(t,e){var o,n,p,r;e.__SV||(window.posthog=e,e._i=[],e.init=function(i,s,a){function g(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}}(p=t.createElement("script")).type="text/javascript",p.crossOrigin="anonymous",p.async=!0,p.src=s.api_host.replace(".i.posthog.com","-assets.i.posthog.com")+"/static/array.js",(r=t.getElementsByTagName("script")[0]).parentNode.insertBefore(p,r);var u=e;for(void 0!==a?u=e[a]=[]:a="posthog",u.people=u.people||[],Object.defineProperty(u,"toString",{configurable:!0,enumerable:!0,writable:!0,value:function(t){var e="posthog";return"posthog"!==a&&(e+="."+a),t||(e+=" (stub)"),e}}),Object.defineProperty(u.people,"toString",{configurable:!0,enumerable:!0,writable:!0,value:function(){return u.toString(1)+".people (stub)"}}),o="init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagResult isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey getNextSurveyStep identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug".split(" "),n=0;n<o.length;n++)g(u,o[n]);e._i.push([i,s,a])},e.__SV=1)}(document,window.posthog||[]);
  window.posthog.init(cfg.key, {api_host: cfg.host, defaults: '2026-08-30', autocapture: false,
    capture_pageview: true, person_profiles: 'identified_only', disable_session_recording: true});
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

/* Raven Crow: Native Banner da Adsterra enquanto o AdSense não aprova. Um por página, rotulado.
   Bloco separado do PostHog para não depender da config dele. Sem popunder/Social Bar/SmartLink. */
(function () {
  const id = 'c8a6205ec43c05a0993cdf30f17a8269';
  if (document.getElementById('container-' + id)) return;
  const anchor = document.getElementById('edicao') || document.getElementById('biblioteca');
  const main = document.querySelector('main');
  if (!anchor && !main) return;
  const box = document.createElement('aside');
  box.setAttribute('aria-label', 'Publicidade');
  box.style.cssText = 'max-width:1150px;margin:32px auto;padding:0 24px';
  box.innerHTML = '<span style="display:block;margin:0 0 8px;color:#b5b2b0;font:11px sans-serif;text-transform:uppercase;letter-spacing:.08em">Publicidade</span><div id="container-' + id + '"></div>';
  if (anchor) anchor.after(box); else main.append(box);
  // só mostra o rótulo quando o anúncio chega (zona pendente ou bloqueador = nada visível)
  box.hidden = true;
  const slot = box.lastElementChild;
  new MutationObserver((_, mo) => { if (slot.children.length) { box.hidden = false; mo.disconnect(); } })
    .observe(slot, {childList: true, subtree: true});
  const s = document.createElement('script');
  s.async = true;
  s.dataset.cfasync = 'false';
  s.src = 'https://bauval.org/21/' + id;
  document.body.append(s);
})();
