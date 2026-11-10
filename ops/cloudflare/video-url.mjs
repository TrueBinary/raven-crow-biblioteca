// "Is this clip URL safe to hand to Buffer?" — read-only check against the public site.
import { createHash } from 'node:crypto';

const CLIP = /^https:\/\/(?:www\.)?ravencrow\.cloud\/clips\/([a-f0-9]{64})\.mp4$/;

export async function verifyPublishedVideo(url, expectedSha256, expectedBytes, { fetchImpl = fetch } = {}) {
  const out = { ok: false, headStatus: 0, rangeStatus: 0, mime: null, reason: '' };
  const m = CLIP.exec(url);
  if (!m || m[1] !== expectedSha256) return { ...out, reason: 'URL is not https://(www.)ravencrow.cloud/clips/<expectedSha256>.mp4' };

  const head = await fetchImpl(url, { method: 'HEAD', signal: AbortSignal.timeout(20000) });
  out.headStatus = head.status;
  out.mime = head.headers.get('content-type');
  if (head.status !== 200) return { ...out, reason: 'HEAD ' + head.status };
  if (head.headers.get('x-raven-migration-stage') !== 'r2') return { ...out, reason: 'not served from R2 (' + head.headers.get('x-raven-migration-stage') + ')' };
  if (out.mime !== 'video/mp4') return { ...out, reason: 'MIME ' + out.mime };
  if (Number(head.headers.get('content-length')) !== expectedBytes) return { ...out, reason: `size ${head.headers.get('content-length')} != ${expectedBytes}` };

  const range = await fetchImpl(url, { headers: { Range: 'bytes=0-15' }, signal: AbortSignal.timeout(20000) });
  out.rangeStatus = range.status;
  await range.arrayBuffer();
  if (range.status !== 206 || range.headers.get('content-range') !== `bytes 0-${Math.min(15, expectedBytes - 1)}/${expectedBytes}`) return { ...out, reason: 'Range not supported correctly' };

  const full = await fetchImpl(url, { signal: AbortSignal.timeout(120000) });
  const sha = createHash('sha256').update(Buffer.from(await full.arrayBuffer())).digest('hex');
  if (sha !== expectedSha256) return { ...out, reason: 'sha256 mismatch ' + sha.slice(0, 12) };
  return { ...out, ok: true };
}

export function findDuplicateClips(entries) {
  const by = new Map();
  for (const e of entries) {
    const sha = CLIP.exec(e.url)?.[1];
    if (sha) by.set(sha, [...(by.get(sha) || []), e.id]);
  }
  return [...by].filter(([, ids]) => ids.length > 1).map(([sha, ids]) => ({ sha, ids }));
}

if (import.meta.url === `file:///${process.argv[1]?.replace(/\\/g, '/')}` || import.meta.url === `file://${process.argv[1]}`) {
  const [url, sha, bytes] = process.argv.slice(2);
  const r = await verifyPublishedVideo(url, sha, Number(bytes));
  console.log(JSON.stringify(r));
  process.exitCode = r.ok ? 0 : 1;
}
