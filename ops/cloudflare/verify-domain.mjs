// Health probe for a public Raven Crow hostname: must reach the Worker, never suspended Render.
export async function verifyHost(url, { expectedMarker = 'r2', fetchImpl = fetch, maxRedirects = 5 } = {}) {
  const seen = new Set();
  let cur = url, res;
  for (;;) {
    if (seen.has(cur) || seen.size > maxRedirects)
      return { url: cur, status: 0, cfRay: false, stage: null, renderSuspend: false, tlsOk: false, redirectLoop: true, ok: false };
    seen.add(cur);
    try {
      res = await fetchImpl(cur, { method: 'HEAD', redirect: 'manual', signal: AbortSignal.timeout(20000) });
    } catch (e) {
      return { url: cur, status: 0, cfRay: false, stage: null, renderSuspend: false, tlsOk: false, redirectLoop: false, error: e.cause?.code || e.message, ok: false };
    }
    const loc = res.headers.get('location');
    if (res.status >= 300 && res.status < 400 && loc) { cur = new URL(loc, cur).href; continue; }
    break;
  }
  const r = {
    url: cur,
    status: res.status,
    cfRay: res.headers.has('cf-ray'),
    stage: res.headers.get('x-raven-migration-stage'),
    renderSuspend: res.headers.has('x-render-routing'),
    tlsOk: cur.startsWith('https:'),
    redirectLoop: false,
  };
  r.ok = r.status === 200 && r.cfRay && !r.renderSuspend && r.tlsOk && r.stage === expectedMarker;
  return r;
}

if (import.meta.url === `file:///${process.argv[1]?.replace(/\\/g, '/')}` || import.meta.url === `file://${process.argv[1]}`) {
  const urls = process.argv.slice(2);
  const results = await Promise.all(urls.map(u => verifyHost(u)));
  console.log(JSON.stringify(results, null, 1));
  process.exitCode = results.every(r => r.ok) ? 0 : 1;
}
