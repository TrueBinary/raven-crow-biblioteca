// Raven Crow production Worker: serves the site from private R2 (RAVEN_MEDIA). No import endpoint.
// GitHub Raw fallback only when env.GITHUB_FALLBACK === "1" (temporary, until main->R2 sync is automatic).
const BASE='https://raw.githubusercontent.com/TrueBinary/raven-crow-biblioteca/main/';
const MIME={'.html':'text/html; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8','.mjs':'text/javascript; charset=utf-8','.json':'application/json; charset=utf-8','.xml':'application/xml; charset=utf-8','.txt':'text/plain; charset=utf-8','.svg':'image/svg+xml','.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.gif':'image/gif','.ico':'image/x-icon','.woff2':'font/woff2','.mp4':'video/mp4','.pdf':'application/pdf'};
export const mimeFor=k=>MIME[/\.[^./]+$/.exec(k.toLowerCase())?.[0]]||'application/octet-stream';
export function resolveKey(raw){let p;try{p=decodeURIComponent(raw)}catch{return null}if(!p.startsWith('/')||p.includes('..')||p.includes('\\')||p.includes('//')||p.includes('\0')||!/^\/[A-Za-z0-9_\-./]*$/.test(p))return null;if(p==='/'||p==='/index.html')return 'index.html';if(/^\/(?:en|es)$/.test(p))return p.slice(1)+'/index.html';if(PAGES.includes(p.slice(1)))return p.slice(1)+'.html';const lp=/^\/(en|es)\/([a-z]+)$/.exec(p);if(lp&&LOCAL_PAGES[lp[1]].includes(lp[2]))return p.slice(1)+'.html';if(/^\/(?:(?:en\/(?:news|column))|(?:es\/(?:noticias|columna))|noticias|coluna)\/[a-z0-9-]{3,100}$/.test(p))return p.slice(1)+'/index.html';return p.endsWith('/')?p.slice(1)+'index.html':p.slice(1)}
export function parseByteRange(value,size){if(value==null)return null;const m=/^bytes=(\d*)-(\d*)$/.exec(value.trim());if(!m||(!m[1]&&!m[2]))return null;const a=m[1]!==''?Number(m[1]):null,b=m[2]!==''?Number(m[2]):null;if((a!==null&&!Number.isSafeInteger(a))||(b!==null&&!Number.isSafeInteger(b))||(a!==null&&b!==null&&b<a))return null;if(!Number.isSafeInteger(size)||size<=0)return {invalid:true};if(a===null){if(!b)return {invalid:true};const len=Math.min(b,size);return {offset:size-len,length:len}}if(a>=size)return {invalid:true};return {offset:a,length:(b===null?size:Math.min(b+1,size))-a}}
const src=key=>key==='index.html'?'index.html':'public/'+key;
const json=(o,status=200)=>new Response(JSON.stringify(o),{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}});
// clips/<sha256>.* never change (new bytes => new hash), so they can be cached for a year.
// Photos keep their name when replaced, so a day (+ a week served stale while revalidating) instead of immutable.
const cache=k=>/^clips\/[a-f0-9]{64}\.(?:mp4|jpg)$/.test(k)?'public, max-age=31536000, immutable':/\.(?:html|json|xml)$/.test(k)?'public, max-age=60':/\.(?:jpe?g|png|webp|gif|svg|ico|woff2)$/.test(k)?'public, max-age=86400, stale-while-revalidate=604800':'public, max-age=300';
function respond(key,obj,method,range){const h=new Headers();obj.writeHttpMetadata(h);h.set('Content-Type',mimeFor(key));h.set('Accept-Ranges','bytes');if(obj.httpEtag)h.set('ETag',obj.httpEtag);h.set('X-Raven-Migration-Stage','r2');h.set('Cache-Control',cache(key));h.set('Content-Length',String(range?.length??obj.size));if(range)h.set('Content-Range','bytes '+range.offset+'-'+(range.offset+range.length-1)+'/'+obj.size);return new Response(method==='HEAD'?null:obj.body,{status:range?206:200,headers:h})}
async function fallback(req,key){try{const h=new Headers();for(const f of ['Range','If-None-Match','If-Modified-Since']){const v=req.headers.get(f);if(v)h.set(f,v)}const up=await fetch(new Request(new URL(src(key),BASE),{method:req.method,headers:h}));const out=new Headers();for(const f of ['Content-Length','Content-Range','ETag','Last-Modified','Accept-Ranges']){const v=up.headers.get(f);if(v)out.set(f,v)}out.set('Content-Type',mimeFor(key));out.set('Cache-Control',cache(key));out.set('X-Raven-Migration-Stage','github-fallback');return new Response(req.method==='HEAD'?null:up.body,{status:up.status,headers:out})}catch{return new Response('Staging source unavailable',{status:502})}}
// Social bar ad: appended before </body> of every full HTML page, so it loads after the content and never blocks it.
const SOCIAL_BAR='<script data-cfasync="false" src="https://bauval.org/14/4615ad4de14cf536c88fee7d3ea00470"></script>';
// Seletor PT · EN · ES no cabeçalho (substitui o botão flutuante do GTranslate). Leva à mesma página no outro
// idioma quando ela existe (link rel=alternate hreflang); senão, à capa daquela edição.
export const LANG_SWITCH='<style>.rc-lang{display:flex;align-items:center;gap:2px;font:700 13px/1 \'DM Sans\',Arial,sans-serif;letter-spacing:.08em}.rc-line .rc-lang{margin-left:auto}.rc-lang a{color:#cfc9c3!important;text-decoration:none!important;padding:10px 8px;border-radius:5px;min-width:36px;text-align:center}.rc-lang a:hover,.rc-lang a:focus-visible{background:#29292d;color:#fff!important;outline:2px solid #d54b50}.rc-lang a[aria-current]{color:#ff7377!important}@media(max-width:600px){.rc-lang a{padding:9px 4px;min-width:32px;font-size:13px}.rc-global-tools{gap:4px!important}.rc-line{gap:8px!important}.rc-top .rc-logo{width:36px!important;height:36px!important}}</style><script>(()=>{const cur=(document.documentElement.lang||"pt").slice(0,2).toLowerCase(),home={pt:"/",en:"/en/",es:"/es/"},alt=l=>document.querySelector(\'link[rel="alternate"][hreflang^="\'+l+\'"]\')?.getAttribute("href");const nav=document.createElement("div");nav.className="rc-lang";nav.setAttribute("role","navigation");nav.setAttribute("aria-label",{pt:"Idioma",en:"Language",es:"Idioma"}[cur]||"Idioma");for(const[l,t]of[["pt","PT"],["en","EN"],["es","ES"]]){const a=document.createElement("a");a.textContent=t;a.lang=a.hreflang=l==="pt"?"pt-BR":l;if(l===cur){a.href=location.pathname;a.setAttribute("aria-current","true")}else a.href=alt(l)||home[l];nav.append(a)}const tools=document.querySelector(".rc-global-tools"),line=document.querySelector(".rc-line");if(tools)tools.prepend(nav);else if(line)line.append(nav);else document.querySelector("header")?.append(nav)})()</script>';
// One favicon for every page (the Raven Crow logo, 48x48 = Google's minimum), declared in <head>.
const ICONS='<link rel="icon" href="/favicon.ico" sizes="48x48"><link rel="icon" type="image/png" sizes="192x192" href="/icon-192.png"><link rel="icon" type="image/png" sizes="512x512" href="/icon-512.png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">';
async function withSocialBar(r){if(r.status!==200||!r.body||!(r.headers.get('Content-Type')||'').startsWith('text/html'))return r;const html=await r.text();const i=html.lastIndexOf('</body>');if(i<0)return new Response(html,{status:200,headers:r.headers});let out=html.slice(0,i)+SOCIAL_BAR+LANG_SWITCH+html.slice(i);const hd=out.indexOf('</head>');if(hd>=0&&!out.slice(0,hd).includes('rel="icon"'))out=out.slice(0,hd)+ICONS+out.slice(hd);const h=new Headers(r.headers);h.set('Content-Length',String(new TextEncoder().encode(out).length));h.delete('ETag');return new Response(out,{status:200,headers:h})}
export default {async fetch(req,env){return withSocialBar(await handle(req,env))}};
// URLs limpas: páginas sem .html, nunca index.html na barra, e erro de digitação leva à página certa.
// Mesmo mapa de news_i18n.SECTIONS: as edições traduzidas usam o nome da seção no idioma.
const LOCAL_SECTIONS=Object.freeze({en:{noticias:'news',coluna:'column'},es:{noticias:'noticias',coluna:'columna'}});
// Páginas traduzidas do site inteiro (PAGE_SLUGS em news_i18n.py): /en/about -> en/about.html.
export const LOCAL_PAGES=Object.freeze({en:['news','column','library','support','about','terms','privacy'],es:['noticias','columna','libros','apoyo','sobre','terminos','privacidad']});
export const PAGES=Object.freeze(['noticias','coluna','livros','apoie','sobre','termos','privacidade','creditos-fotos']);
const ALIASES=Object.freeze({'termos-de-uso':'/termos','politica-de-privacidade':'/privacidade','biblioteca':'/livros','inicio':'/','home':'/'});
function distance(a,b){const d=Array.from({length:b.length+1},(_,i)=>i);for(let i=1;i<=a.length;i++){let prev=d[0];d[0]=i;for(let j=1;j<=b.length;j++){const t=d[j];d[j]=Math.min(d[j]+1,d[j-1]+1,prev+(a[i-1]===b[j-1]?0:1));prev=t}}return d[b.length]}
export function cleanRoute(path){
 if(path.endsWith('/index.html'))return [path.slice(0,-'index.html'.length),301];
 const moved=/^\/(en|es)\/(noticias|coluna)\/([a-z0-9-]{3,100})(?:\/.*)?$/.exec(path);if(moved){const local=LOCAL_SECTIONS[moved[1]][moved[2]];if(local!==moved[2])return ['/'+moved[1]+'/'+local+'/'+moved[3]+'/',301]}
 const lp=/^\/(en|es)\/([a-z]+)(?:\.html|\/)$/.exec(path);if(lp&&LOCAL_PAGES[lp[1]].includes(lp[2]))return ['/'+lp[1]+'/'+lp[2],301];
 const html=/^\/([a-z-]+)\.html$/.exec(path);if(html&&PAGES.includes(html[1]))return ['/'+html[1],301];
 const seg=/^\/([A-Za-z-]{2,40})\/?$/.exec(path);if(!seg)return null;
 const name=seg[1].toLowerCase();
 if(PAGES.includes(name))return name===seg[1]&&!path.endsWith('/')?null:['/'+name,301];
 if(ALIASES[name])return [ALIASES[name],301];
 if(name==='en'||name==='es'||name.length<4)return null;
 // Erro de digitação (colunas, noticia, sobr): só com um candidato claro; 302 porque é palpite.
 let best=null,score=3,tie=false;for(const page of PAGES){const d=distance(name,page);if(d<score){best=page;score=d;tie=false}else if(d===score)tie=true}
 return best&&!tie?['/'+best,302]:null;
}
// Índices antigos com nome em português: vão para o índice traduzido do idioma.
const SECTION_REDIRECTS=Object.freeze({
 '/en/noticias':['/en/news',301],'/en/noticias/':['/en/news',301],
 '/en/coluna':['/en/column',301],'/en/coluna/':['/en/column',301],
 '/es/coluna':['/es/columna',301],'/es/coluna/':['/es/columna',301],
});
// Show a branded error only for navigable pages, never for broken JS/CSS/media.
async function notFound(req,env,path){
 const isPage=!/\.[A-Za-z0-9]{1,8}$/.test(path)||path.endsWith('.html');
 if(isPage){
  try{
   const page=await env.RAVEN_MEDIA.get('404.html');
   if(page){
    return new Response(req.method==='HEAD'?null:page.body,{status:404,headers:{
     'Content-Type':'text/html; charset=utf-8',
     'Cache-Control':'public, max-age=60',
     'Content-Length':String(page.size),
     'X-Robots-Tag':'noindex',
     'X-Raven-Migration-Stage':'r2'
    }});
   }
   // Temporary source until the regular 15-minute release copies 404.html to R2.
   if(env.GITHUB_FALLBACK==='1'){
    const upstream=await fallback(req,'404.html');
    if(upstream.status===200){
     const headers=new Headers(upstream.headers);
     headers.set('Content-Type','text/html; charset=utf-8');
     headers.set('Cache-Control','public, max-age=60');
     headers.set('X-Robots-Tag','noindex');
     return new Response(req.method==='HEAD'?null:upstream.body,{status:404,headers});
    }
   }
  }catch{/* Preserve the existing 404 if the error page itself is unavailable. */}
 }
 return new Response(req.method==='HEAD'?null:'Not Found',{status:404,headers:{'Cache-Control':'public, max-age=60'}});
}
async function handle(req,env){
 const path=new URL(req.url).pathname;
 if(path==='/__raven_migration_health')return json({status:'production',R2:true,domainCutover:true,githubFallback:env.GITHUB_FALLBACK==='1'});
 if(path.startsWith('/__migration/'))return new Response('Not Found',{status:404});
 if(req.method!=='GET'&&req.method!=='HEAD')return new Response('Method Not Allowed',{status:405,headers:{Allow:'GET, HEAD'}});
 const clean=cleanRoute(path);if(clean)return new Response(null,{status:clean[1],headers:{Location:clean[0]+new URL(req.url).search,'Cache-Control':'public, max-age=300'}});
 const section=SECTION_REDIRECTS[path];if(section)return new Response(null,{status:section[1],headers:{Location:section[0],'Cache-Control':'public, max-age=300'}});
 const key=resolveKey(path);if(!key)return new Response('Invalid path',{status:400});
 const head=await env.RAVEN_MEDIA.head(key);
 if(!head){
  if(env.GITHUB_FALLBACK==='1'){
   const upstream=await fallback(req,key);
   return upstream.status===404?notFound(req,env,path):upstream;
  }
  return notFound(req,env,path);
 }
 const inm=req.headers.get('If-None-Match');if(inm&&(inm.trim()==='*'||inm.split(',').some(t=>t.trim().replace(/^W\//,'')===head.httpEtag.replace(/^W\//,''))))return new Response(null,{status:304,headers:{ETag:head.httpEtag,'Cache-Control':cache(key)}});
 if(req.method==='HEAD')return respond(key,head,'HEAD',null);
 const range=parseByteRange(req.headers.get('Range'),head.size);
 if(range?.invalid)return new Response(null,{status:416,headers:{'Content-Range':'bytes */'+head.size,'Accept-Ranges':'bytes'}});
 const body=await env.RAVEN_MEDIA.get(key,range?{range}:undefined);
 return body?respond(key,body,'GET',range):new Response('Not Found',{status:404});
}
