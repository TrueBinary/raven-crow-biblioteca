/* Raven Crow: static ad placement and licensed, illustrative editorial photographs. */
(async function(){
const root=document.getElementById('editorial-feed');
if(!root)return;
// Mesma página nas três línguas (build-i18n-site.py): o idioma vem do <html lang>.
const LANG=(document.documentElement.lang||'pt').slice(0,2).toLowerCase();
const t={
 pt:{img:'Imagem ilustrativa: ',news:'Notícias',lead:'Confira a análise completa.',min:' min de leitura',file:'Foto ilustrativa de arquivo',all:'TODAS AS MATÉRIAS',latest:'ÚLTIMAS NOTÍCIAS',analysis:'Análise',more:'Leia a matéria completa.',credits:'Créditos e licenças das fotografias',hot:'EM ALTA',column:'COLUNA DO CORVO',columnLink:'Leia nossas análises e investigações',one:'matéria',many:'matérias',archive:' no acervo',none:'Nenhuma matéria encontrada. Experimente outra busca.',error:'Não foi possível carregar as notícias agora.',newsPath:'/noticias/',columnPath:'/coluna'},
 en:{img:'Illustrative image: ',news:'News',lead:'Read the full analysis.',min:' min read',file:'Illustrative file photo',all:'ALL STORIES',latest:'LATEST NEWS',analysis:'Analysis',more:'Read the full story.',credits:'Photo credits and licenses',hot:'TRENDING',column:"THE CROW'S COLUMN",columnLink:'Read our analysis and investigations',one:'story',many:'stories',archive:' in the archive',none:'No stories found. Try another search.',error:'The news could not be loaded right now.',newsPath:'/en/news/',columnPath:'/en/column'},
 es:{img:'Imagen ilustrativa: ',news:'Noticias',lead:'Lee el análisis completo.',min:' min de lectura',file:'Foto ilustrativa de archivo',all:'TODAS LAS NOTAS',latest:'ÚLTIMAS NOTICIAS',analysis:'Análisis',more:'Lee la nota completa.',credits:'Créditos y licencias de las fotografías',hot:'TENDENCIAS',column:'COLUMNA DEL CUERVO',columnLink:'Lee nuestros análisis e investigaciones',one:'nota',many:'notas',archive:' en el archivo',none:'No se encontraron notas. Prueba otra búsqueda.',error:'No fue posible cargar las noticias ahora.',newsPath:'/es/noticias/',columnPath:'/es/columna'}
}[LANG];
if(!t)return;
const make=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e};
const imagePath=(a,assets)=>{
 // Same-origin absolute URLs (https://ravencrow.cloud/x.jpg) are treated as site-relative paths.
 const explicit=(typeof a.image==='string'?a.image:'').replace(/^https:\/\/(?:www\.)?ravencrow\.cloud\//,'');
 if(/^\/?(?:(?:images|editorial)\/)?[a-zA-Z0-9/_-]+\.(?:jpg|jpeg|png|webp)$/.test(explicit)&&!explicit.includes('..'))return '/'+explicit.replace(/^\//,'');
 const photo=(assets.photos||{})[a.id];
 if(typeof photo==='string'&&/^editorial\/photos\/[a-z0-9-]+\.jpg$/.test(photo))return '/'+photo;
 const cover=(assets.covers||{})[a.id];
 return typeof cover==='string'&&/^editorial\/covers\/[a-z0-9-]+\.svg$/.test(cover)?'/'+cover:null;
};
// Em inglês/espanhol só entra a matéria com tradução completa (a mesma regra de news_i18n.py).
const localize=a=>{if(LANG==='pt')return a;const b=a[LANG];if(!b||!['title','facts','analysis','counterpoint'].every(k=>typeof b[k]==='string'&&b[k].trim()))return null;return {...a,title:b.title,subtitle:b.subtitle||'',category:b.category||'',facts:b.facts,analysis:b.analysis,counterpoint:b.counterpoint}};
const href=a=>t.newsPath+encodeURIComponent(a.id)+'/';
const readingTime=a=>Math.max(2,Math.ceil(((a.facts||'')+' '+(a.analysis||'')+' '+(a.counterpoint||'')).split(/\s+/).length/210));
const formatDate=date=>{if(!/^\d{4}-\d{2}-\d{2}$/.test(date||''))return 'Raven Crow';const [y,m,d]=date.split('-');return LANG==='en'?m+'/'+d+'/'+y:d+'/'+m+'/'+y};
const image=(path,cls,alt,eager=false)=>{const el=make('img',cls);el.src=path;el.alt=alt;el.loading=eager?'eager':'lazy';el.decoding='async';if(eager)el.fetchPriority='high';return el};
try{
 const [response,manifest]=await Promise.all([fetch('/editorial-feed.json',{cache:'no-store'}),fetch('/editorial-images.json').then(r=>r.ok?r.json():{}).catch(()=>({}))]);
 if(!response.ok)throw Error('feed unavailable');
 const feed=await response.json(),isFullArchive=root.dataset.feedMode==='all';
 const allStories=Array.isArray(feed.articles)?feed.articles.filter(a=>a&&/^[a-z0-9-]{3,100}$/.test(a.id)).map(localize).filter(Boolean):[];
 const query=new URLSearchParams(location.search).get('q')?.trim().toLocaleLowerCase('pt-BR')||'';
 const matches=isFullArchive&&query?allStories.filter(a=>(a.title+' '+(a.subtitle||'')+' '+(a.category||'')).toLocaleLowerCase('pt-BR').includes(query)):allStories;
 const stories=isFullArchive?matches:matches.slice(0,8),assets=manifest&&typeof manifest==='object'?manifest:{};
 if(isFullArchive){const count=document.getElementById('news-count');if(count)count.textContent=stories.length+' '+(stories.length===1?t.one:t.many)+t.archive+(query?': “'+query+'”':'')}
 if(!stories.length){if(!isFullArchive)root.hidden=true;else{const main=root.querySelector('.rc-mag-main');if(main)main.textContent=t.none}return}
 root.classList.add('rc-magazine');
 // WebP de 640/1280 px no lugar do JPEG original (alguns têm 4000 px e 2,7 MB).
 const sized=(img,a,sizes)=>{const v=(assets.photoVariants||{})[a.id];if(v&&!a.image&&typeof v.srcset==='string'&&img.src.endsWith('.jpg')){img.srcset=v.srcset.split(',').map(x=>'/'+x.trim()).join(', ');img.sizes=sizes;img.src='/'+v.src}return img};
 const main=root.querySelector('.rc-mag-main')||make('div','rc-mag-main');
 const side=root.querySelector('.rc-mag-side')||make('aside','rc-mag-side');
 if(!main.isConnected)root.append(main);if(!side.isConnected)root.append(side);
 // A capa já vem desenhada do build (frontpage_static.py): redesenhar só faria a página pular.
 if(!(main.dataset.ssr==='1'&&!isFullArchive)){
 main.replaceChildren();
 const lead=stories[0],hero=make('a','rc-mag-hero');
 hero.href=href(lead);hero.id=lead.id;
 const leadPhoto=imagePath(lead,assets);
 if(leadPhoto){const pic=sized(image(leadPhoto,'rc-mag-hero-image',t.img+lead.title,true),lead,'(max-width: 900px) 100vw, 900px');pic.onerror=()=>pic.remove();hero.append(pic)}
 const heroContent=make('div','rc-mag-hero-content');
 heroContent.append(make('span','rc-mag-tag',lead.category||t.news),make('h2','',lead.title),make('p','',lead.subtitle||t.lead));
 heroContent.append(make('span','rc-mag-meta',formatDate(lead.date)+'  ·  '+readingTime(lead)+t.min+(leadPhoto?'  ·  '+t.file:'')));
 hero.append(heroContent);main.append(hero);
 main.append(make('h2','rc-mag-section-title',isFullArchive?t.all:t.latest));
 const list=make('div','rc-mag-list');main.append(list);
 for(const a of (isFullArchive?stories.slice(1):stories.slice(1,6))){
  const link=make('a','rc-mag-item');link.href=href(a);link.id=a.id;
  const tile=make('div','rc-mag-thumbnail'),asset=imagePath(a,assets);
  if(asset){const pic=sized(image(asset,'rc-mag-item-image',t.img+a.title),a,'(max-width: 600px) 40vw, 260px');pic.onerror=()=>{tile.replaceChildren(image('/raven-logo.webp','rc-mag-placeholder',''));tile.classList.add('rc-mag-thumbnail-empty')};tile.append(pic)}
  else{tile.classList.add('rc-mag-thumbnail-empty');tile.append(image('/raven-logo.webp','rc-mag-placeholder',''))}
  const content=make('div','rc-mag-item-body');
  content.append(make('span','rc-mag-tag',a.category||t.analysis),make('h3','',a.title),make('p','',a.subtitle||t.more),make('span','rc-mag-meta',formatDate(a.date)+'  ·  '+readingTime(a)+t.min));
  link.append(tile,content);list.append(link);
 }
 if(assets.photos&&Object.keys(assets.photos).length){const credits=make('a','rc-mag-photo-credits',t.credits);credits.href='/creditos-fotos';main.append(credits)}
 }
 for(const old of side.querySelectorAll('.rc-mag-popular,.rc-mag-column'))old.remove();
 const popular=make('section','rc-mag-popular');popular.append(make('h2','rc-mag-section-title',t.hot));
 stories.slice(0,4).forEach((a,i)=>{const link=make('a','rc-mag-popular-item');link.href=href(a);link.append(make('strong','',String(i+1)),make('span','',a.title));popular.append(link)});
 side.append(popular);
 const column=make('section','rc-mag-column');column.append(make('h2','rc-mag-section-title',t.column));
 const columnLink=make('a','rc-mag-column-link',t.columnLink);columnLink.href=t.columnPath;column.append(columnLink);side.append(column);
 if(isFullArchive&&location.hash){const id=decodeURIComponent(location.hash.slice(1));if(/^[a-z0-9-]{3,100}$/.test(id))root.querySelector('#'+id)?.scrollIntoView({block:'start'})}
}catch(error){
 const main=root.querySelector('.rc-mag-main')||root;
 const message=make('p','rc-mag-error',t.error);
 main.replaceChildren(message);
}
})();
