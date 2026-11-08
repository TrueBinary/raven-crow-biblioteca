// Raven Crow production Worker: serves the site from private R2 (RAVEN_MEDIA). No import endpoint.
// GitHub Raw fallback only when env.GITHUB_FALLBACK === "1" (temporary, until main->R2 sync is automatic).
const BASE='https://raw.githubusercontent.com/TrueBinary/raven-crow-biblioteca/main/';
const MIME={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.xml':'application/xml; charset=utf-8','.txt':'text/plain; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.gif':'image/gif','.ico':'image/x-icon','.woff2':'font/woff2','.mp4':'video/mp4','.pdf':'application/pdf'};
export const mimeFor=k=>MIME[/\.[^./]+$/.exec(k.toLowerCase())?.[0]]||'application/octet-stream';
export function resolveKey(raw){let p;try{p=decodeURIComponent(raw)}catch{return null}if(!p.startsWith('/')||p.includes('..')||p.includes('\\')||p.includes('//')||p.includes('\0')||!/^\/[A-Za-z0-9_\-./]*$/.test(p))return null;if(p==='/'||p==='/index.html')return 'index.html';if(/^\/(?:noticias|coluna)\/[a-z0-9-]{3,100}$/.test(p))return p.slice(1)+'/index.html';return p.endsWith('/')?p.slice(1)+'index.html':p.slice(1)}
export function parseByteRange(value,size){if(value==null)return null;const m=/^bytes=(\d*)-(\d*)$/.exec(value.trim());if(!m||(!m[1]&&!m[2]))return null;const a=m[1]!==''?Number(m[1]):null,b=m[2]!==''?Number(m[2]):null;if((a!==null&&!Number.isSafeInteger(a))||(b!==null&&!Number.isSafeInteger(b))||(a!==null&&b!==null&&b<a))return null;if(!Number.isSafeInteger(size)||size<=0)return {invalid:true};if(a===null){if(!b)return {invalid:true};const len=Math.min(b,size);return {offset:size-len,length:len}}if(a>=size)return {invalid:true};return {offset:a,length:(b===null?size:Math.min(b+1,size))-a}}
const src=key=>key==='index.html'?'index.html':'public/'+key;
const json=(o,status=200)=>new Response(JSON.stringify(o),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}});
// clips/<sha256>.* never change (new bytes => new hash), so they can be cached for a year.
const cache=k=>/^clips\/[a-f0-9]{64}\.(?:mp4|jpg)$/.test(k)?'public, max-age=31536000, immutable':/\.(?:html|json|xml)$/.test(k)?'public, max-age=60':'public, max-age=300';
function respond(key,obj,method,range){const h=new Headers();obj.writeHttpMetadata(h);h.set('Content-Type',mimeFor(key));h.set('Accept-Ranges','bytes');if(obj.httpEtag)h.set('ETag',obj.httpEtag);h.set('X-Raven-Migration-Stage','r2');h.set('Cache-Control',cache(key));h.set('Content-Length',String(range?.length??obj.size));if(range)h.set('Content-Range','bytes '+range.offset+'-'+(range.offset+range.length-1)+'/'+obj.size);return new Response(method==='HEAD'?null:obj.body,{status:range?206:200,headers:h})}
async function fallback(req,key){try{const h=new Headers();for(const f of ['Range','If-None-Match','If-Modified-Since']){const v=req.headers.get(f);if(v)h.set(f,v)}const up=await fetch(new Request(new URL(src(key),BASE),{method:req.method,headers:h}));const out=new Headers();for(const f of ['Content-Length','Content-Range','ETag','Last-Modified','Accept-Ranges']){const v=up.headers.get(f);if(v)out.set(f,v)}out.set('Content-Type',mimeFor(key));out.set('Cache-Control',cache(key));out.set('X-Raven-Migration-Stage','github-fallback');return new Response(req.method==='HEAD'?null:up.body,{status:up.status,headers:out})}catch{return new Response('Staging source unavailable',{status:502})}}
// Social bar ad: appended before </body> of every full HTML page, so it loads after the content and never blocks it.
const SOCIAL_BAR='<script data-cfasync="false" src="https://bauval.org/14/4615ad4de14cf536c88fee7d3ea00470"></script>';
async function withSocialBar(r){if(r.status!==200||!r.body||!(r.headers.get('Content-Type')||'').startsWith('text/html'))return r;const html=await r.text();const i=html.lastIndexOf('</body>');if(i<0)return new Response(html,{status:200,headers:r.headers});const out=html.slice(0,i)+SOCIAL_BAR+html.slice(i);const h=new Headers(r.headers);h.set('Content-Length',String(new TextEncoder().encode(out).length));h.delete('ETag');return new Response(out,{status:200,headers:h})}
export default {async fetch(req,env){return withSocialBar(await handle(req,env))}};
async function handle(req,env){
 const path=new URL(req.url).pathname;
 if(path==='/__raven_migration_health')return json({status:'production',R2:true,domainCutover:true,githubFallback:env.GITHUB_FALLBACK==='1'});
 if(path.startsWith('/__migration/'))return new Response('Not Found',{status:404});
 if(req.method!=='GET'&&req.method!=='HEAD')return new Response('Method Not Allowed',{status:405,headers:{Allow:'GET, HEAD'}});
 const key=resolveKey(path);if(!key)return new Response('Invalid path',{status:400});
 const head=await env.RAVEN_MEDIA.head(key);if(!head)return env.GITHUB_FALLBACK==='1'?fallback(req,key):new Response('Not Found',{status:404,headers:{'Cache-Control':'public, max-age=60'}});
 const inm=req.headers.get('If-None-Match');if(inm&&(inm.trim()==='*'||inm.split(',').some(t=>t.trim().replace(/^W\//,'')===head.httpEtag.replace(/^W\//,''))))return new Response(null,{status:304,headers:{ETag:head.httpEtag,'Cache-Control':cache(key)}});
 if(req.method==='HEAD')return respond(key,head,'HEAD',null);
 const range=parseByteRange(req.headers.get('Range'),head.size);
 if(range?.invalid)return new Response(null,{status:416,headers:{'Content-Range':'bytes */'+head.size,'Accept-Ranges':'bytes'}});
 const body=await env.RAVEN_MEDIA.get(key,range?{range}:undefined);
 return body?respond(key,body,'GET',range):new Response('Not Found',{status:404});
}
