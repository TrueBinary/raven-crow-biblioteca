/* Editorial archive: draw from the same audited news feed, never duplicate or invent stories. */
(async function(){
const root=document.getElementById('rc-col-archive-list');if(!root)return;
const LANG=(document.documentElement.lang||'pt').slice(0,2).toLowerCase();
const t={pt:{path:'/noticias/',file:'Imagem ilustrativa de arquivo',cat:'ANÁLISE',arc:' · ARQUIVO',fallback:'Análise Raven Crow',more:'Leia o texto e consulte as fontes.',empty:'Nenhum artigo arquivado no momento.',error:'Não foi possível carregar o arquivo agora.',all:'Acesse as notícias e análises',hub:'/noticias'},
 en:{path:'/en/news/',file:'Illustrative file photo',cat:'ANALYSIS',arc:' · ARCHIVE',fallback:'Raven Crow analysis',more:'Read the story and check the sources.',empty:'No archived stories right now.',error:'The archive could not be loaded right now.',all:'Go to news and analysis',hub:'/en/news'},
 es:{path:'/es/noticias/',file:'Foto ilustrativa de archivo',cat:'ANÁLISIS',arc:' · ARCHIVO',fallback:'Análisis Raven Crow',more:'Lee la nota y consulta las fuentes.',empty:'No hay notas archivadas por ahora.',error:'No fue posible cargar el archivo ahora.',all:'Ve a noticias y análisis',hub:'/es/noticias'}}[LANG]||null;
if(!t)return;
// Em inglês/espanhol só a matéria com tradução completa (regra de news_i18n.py).
const localize=a=>{if(LANG==='pt')return a;const b=a[LANG];if(!b||!['title','facts','analysis','counterpoint'].every(k=>typeof b[k]==='string'&&b[k].trim()))return null;return {...a,slug:/^[a-z0-9-]{3,100}$/.test(b.slug||'')?b.slug:a.id,title:b.title,subtitle:b.subtitle||'',category:b.category||''}};
const make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e};
try{
 const [res,assetRes]=await Promise.all([fetch('/editorial-feed.json',{cache:'no-store'}),fetch('/editorial-images.json').catch(()=>null)]);
 if(!res.ok)throw Error('feed not available');
 const feed=await res.json();
 const assets=assetRes&&assetRes.ok?await assetRes.json():{};
 const seen=new Set(),items=[];
 for(const article of (Array.isArray(feed.articles)?feed.articles:[]).map(x=>x&&localize(x))){
   if(!article||!(/^[a-z0-9-]{3,100}$/.test(article.id))||seen.has(article.id))continue;
   seen.add(article.id);items.push(article)
 }
 items.sort((a,b)=>String(b.date||'').localeCompare(String(a.date||'')));
 root.replaceChildren();
 for(const article of items){
   const a=make('a','rc-col-archive-item');a.href=t.path+encodeURIComponent(article.slug||article.id)+'/';
   const thumb=make('div','rc-col-thumb'),photo=assets.photos&&assets.photos[article.id];
   const img=make('img',typeof photo==='string'?'':'rc-col-thumb-placeholder');
   img.src=typeof photo==='string'&&/^editorial\/photos\/[a-z0-9-]+\.jpg$/.test(photo)?'/'+photo:'/raven-logo.webp';
   img.alt=typeof photo==='string'?t.file:'';
   img.loading='lazy';
   img.onerror=()=>{img.src='/raven-logo.webp';img.alt='';img.className='rc-col-thumb-placeholder';img.onerror=null};
   thumb.append(img);
   const body=make('div','rc-col-archive-body');
   body.append(make('span','rc-col-archive-category',(article.category||t.cat)+t.arc),make('h3','',article.title||t.fallback));
   body.append(make('p','',article.subtitle||t.more));
   const date=make('time','',String(article.date||'').replace(/^(\d{4})-(\d{2})-(\d{2})$/,LANG==='en'?'$2/$3/$1':'$3/$2/$1'));
   if(/^\d{4}-\d{2}-\d{2}$/.test(article.date||''))date.dateTime=article.date;
   body.append(date);
   a.append(thumb,body);root.append(a);
 }
 if(!items.length)root.append(make('p','rc-col-loading',t.empty));
}catch(_){
 root.replaceChildren();
 const p=make('p','rc-col-loading',t.error);
 const a=make('a','',t.all);a.href=t.hub;p.append(' ',a);root.append(p);
}
})();