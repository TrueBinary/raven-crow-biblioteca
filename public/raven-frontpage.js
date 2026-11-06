/* Raven Crow: static ad placement and licensed, illustrative editorial photographs. */
(async function(){
const root=document.getElementById('editorial-feed');
if(!root)return;
const make=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e};
const imagePath=(a,assets)=>{
 const explicit=typeof a.image==='string'?a.image:'';
 if(/^\/?(?:images|editorial)\/[a-zA-Z0-9/_-]+\.(?:jpg|jpeg|png|webp)$/.test(explicit))return explicit.replace(/^\//,'');
 const photo=(assets.photos||{})[a.id];
 return typeof photo==='string'&&/^editorial\/photos\/[a-z0-9-]+\.jpg$/.test(photo)?photo:null;
};
const readingTime=a=>Math.max(2,Math.ceil(((a.facts||'')+' '+(a.analysis||'')+' '+(a.counterpoint||'')).split(/\s+/).length/210));
const formatDate=date=>{if(!/^\d{4}-\d{2}-\d{2}$/.test(date||''))return 'Raven Crow';const [y,m,d]=date.split('-');return d+'/'+m+'/'+y};
const image=(path,cls,alt,eager=false)=>{const el=make('img',cls);el.src=path;el.alt=alt;el.loading=eager?'eager':'lazy';el.decoding='async';if(eager)el.fetchPriority='high';return el};
try{
 const [response,manifest]=await Promise.all([fetch('editorial-feed.json',{cache:'no-store'}),fetch('editorial-images.json').then(r=>r.ok?r.json():{}).catch(()=>({}))]);
 if(!response.ok)throw Error('feed unavailable');
 const feed=await response.json(),isFullArchive=root.dataset.feedMode==='all';
 const allStories=Array.isArray(feed.articles)?feed.articles.filter(a=>a&&/^[a-z0-9-]{3,100}$/.test(a.id)):[];
 const query=new URLSearchParams(location.search).get('q')?.trim().toLocaleLowerCase('pt-BR')||'';
 const matches=isFullArchive&&query?allStories.filter(a=>(a.title+' '+(a.subtitle||'')+' '+(a.category||'')).toLocaleLowerCase('pt-BR').includes(query)):allStories;
 const stories=isFullArchive?matches:matches.slice(0,8),assets=manifest&&typeof manifest==='object'?manifest:{};
 if(isFullArchive){const count=document.getElementById('news-count');if(count)count.textContent=stories.length+' '+(stories.length===1?'matéria':'matérias')+' no acervo'+(query?' para “'+query+'”':'')}
 if(!stories.length){if(!isFullArchive)root.hidden=true;else{const main=root.querySelector('.rc-mag-main');if(main)main.textContent='Nenhuma matéria encontrada. Experimente outra busca.'}return}
 root.classList.add('rc-magazine');
 const main=root.querySelector('.rc-mag-main')||make('div','rc-mag-main');
 const side=root.querySelector('.rc-mag-side')||make('aside','rc-mag-side');
 if(!main.isConnected)root.append(main);if(!side.isConnected)root.append(side);
 main.replaceChildren();
 const lead=stories[0],hero=make('a','rc-mag-hero');
 hero.href='noticias/'+encodeURIComponent(lead.id)+'/';hero.id=lead.id;
 const leadPhoto=imagePath(lead,assets);
 if(leadPhoto){const pic=image(leadPhoto,'rc-mag-hero-image','Imagem ilustrativa: '+lead.title,true);pic.onerror=()=>pic.remove();hero.append(pic)}
 const heroContent=make('div','rc-mag-hero-content');
 heroContent.append(make('span','rc-mag-tag',lead.category||'Notícias'),make('h2','',lead.title),make('p','',lead.subtitle||'Confira a análise completa.'));
 heroContent.append(make('span','rc-mag-meta',formatDate(lead.date)+'  ·  '+readingTime(lead)+' min de leitura'+(leadPhoto?'  ·  Foto ilustrativa de arquivo':'')));
 hero.append(heroContent);main.append(hero);
 main.append(make('h2','rc-mag-section-title',isFullArchive?'TODAS AS MATÉRIAS':'ÚLTIMAS NOTÍCIAS'));
 const list=make('div','rc-mag-list');main.append(list);
 for(const a of (isFullArchive?stories.slice(1):stories.slice(1,6))){
  const link=make('a','rc-mag-item');link.href='noticias/'+encodeURIComponent(a.id)+'/';link.id=a.id;
  const tile=make('div','rc-mag-thumbnail'),asset=imagePath(a,assets);
  if(asset){const pic=image(asset,'rc-mag-item-image','Imagem ilustrativa: '+a.title);pic.onerror=()=>{tile.replaceChildren(image('raven-logo.webp','rc-mag-placeholder',''));tile.classList.add('rc-mag-thumbnail-empty')};tile.append(pic)}
  else{tile.classList.add('rc-mag-thumbnail-empty');tile.append(image('raven-logo.webp','rc-mag-placeholder',''))}
  const content=make('div','rc-mag-item-body');
  content.append(make('span','rc-mag-tag',a.category||'Análise'),make('h3','',a.title),make('p','',a.subtitle||'Leia a matéria completa.'),make('span','rc-mag-meta',formatDate(a.date)+'  ·  '+readingTime(a)+' min de leitura'));
  link.append(tile,content);list.append(link);
 }
 if(assets.photos&&Object.keys(assets.photos).length){const credits=make('a','rc-mag-photo-credits','Créditos e licenças das fotografias');credits.href='creditos-fotos.html';main.append(credits)}
 for(const old of side.querySelectorAll('.rc-mag-popular,.rc-mag-column'))old.remove();
 const popular=make('section','rc-mag-popular');popular.append(make('h2','rc-mag-section-title','EM ALTA'));
 stories.slice(0,4).forEach((a,i)=>{const link=make('a','rc-mag-popular-item');link.href='noticias/'+encodeURIComponent(a.id)+'/';link.append(make('strong','',String(i+1)),make('span','',a.title));popular.append(link)});
 side.append(popular);
 const column=make('section','rc-mag-column');column.append(make('h2','rc-mag-section-title','COLUNA DO CORVO'));
 const columnLink=make('a','rc-mag-column-link','Leia nossas análises e investigações');columnLink.href='coluna.html';column.append(columnLink);side.append(column);
 if(isFullArchive&&location.hash){const id=decodeURIComponent(location.hash.slice(1));if(/^[a-z0-9-]{3,100}$/.test(id))root.querySelector('#'+id)?.scrollIntoView({block:'start'})}
}catch(error){
 const main=root.querySelector('.rc-mag-main')||root;
 const message=make('p','rc-mag-error','Não foi possível carregar as notícias agora.');
 main.replaceChildren(message);
}
})();
