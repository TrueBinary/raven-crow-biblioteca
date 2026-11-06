/* Editorial archive: draw from the same audited news feed, never duplicate or invent stories. */
(async function(){
const root=document.getElementById('rc-col-archive-list');if(!root)return;
const make=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e};
try{
 const [res,assetRes]=await Promise.all([fetch('editorial-feed.json',{cache:'no-store'}),fetch('editorial-images.json').catch(()=>null)]);
 if(!res.ok)throw Error('feed not available');
 const feed=await res.json();
 const assets=assetRes&&assetRes.ok?await assetRes.json():{};
 const seen=new Set(),items=[];
 for(const article of Array.isArray(feed.articles)?feed.articles:[]){
   if(!article||!(/^[a-z0-9-]{3,100}$/.test(article.id))||seen.has(article.id))continue;
   seen.add(article.id);items.push(article)
 }
 items.sort((a,b)=>String(b.date||'').localeCompare(String(a.date||'')));
 root.replaceChildren();
 for(const article of items){
   const a=make('a','rc-col-archive-item');a.href='noticias/'+encodeURIComponent(article.id)+'/';
   const thumb=make('div','rc-col-thumb'),photo=assets.photos&&assets.photos[article.id];
   const img=make('img',typeof photo==='string'?'':'rc-col-thumb-placeholder');
   img.src=typeof photo==='string'&&/^editorial\/photos\/[a-z0-9-]+\.jpg$/.test(photo)?photo:'raven-logo.webp';
   img.alt=typeof photo==='string'?'Imagem ilustrativa de arquivo':'';
   img.loading='lazy';
   img.onerror=()=>{img.src='raven-logo.webp';img.alt='';img.className='rc-col-thumb-placeholder';img.onerror=null};
   thumb.append(img);
   const body=make('div','rc-col-archive-body');
   body.append(make('span','rc-col-archive-category',(article.category||'ANÁLISE')+' · ARQUIVO'),make('h3','',article.title||'Análise Raven Crow'));
   body.append(make('p','',article.subtitle||'Leia o texto e consulte as fontes.'));
   const date=make('time','',String(article.date||'').replace(/^(\d{4})-(\d{2})-(\d{2})$/,'$3/$2/$1'));
   if(/^\d{4}-\d{2}-\d{2}$/.test(article.date||''))date.dateTime=article.date;
   body.append(date);
   a.append(thumb,body);root.append(a);
 }
 if(!items.length)root.append(make('p','rc-col-loading','Nenhum artigo arquivado no momento.'));
}catch(_){
 root.replaceChildren();
 const p=make('p','rc-col-loading','Não foi possível carregar o arquivo agora.');
 const a=make('a','','Acesse as notícias e análises');a.href='noticias.html';p.append(' ',a);root.append(p);
}
})();