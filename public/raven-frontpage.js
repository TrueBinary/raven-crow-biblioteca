/* Raven Crow editorial frontpage. Never invent headlines or substitute unrelated imagery. */
(async function(){
const root=document.getElementById('editorial-feed');if(!root)return;
const make=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e};
const imagePath=(a,assets)=>{
 const explicit=typeof a.image==='string'?a.image:'';
 if(/^\/?(?:images|editorial)\/[a-zA-Z0-9/_-]+\.(?:jpg|jpeg|png|webp)$/.test(explicit))return explicit.replace(/^\//,'');
 const key=String(a.id||'').replace(/-2026$/,'');
 const folders=Array.isArray(assets.carousels)?assets.carousels:[];
 const folder=folders.find(x=>x.endsWith('-'+a.id)||x.endsWith('-'+key)||x.includes(key));
 return (assets.photos&&assets.photos[a.id])||(folder?'carrosseis/'+folder+'/slide1.png':null)||(assets.covers&&assets.covers[a.id])||null;
};
const readingTime=a=>Math.max(2,Math.ceil(((a.facts||'')+' '+(a.analysis||'')+' '+(a.counterpoint||'')).split(/\s+/).length/210));
const formatDate=date=>{if(!/^\d{4}-\d{2}-\d{2}$/.test(date||''))return 'Raven Crow';const [y,m,d]=date.split('-');return d+'/'+m+'/'+y};
const image=(path,cls,alt,eager=false)=>{const el=make('img',cls);el.src=path;el.alt=alt;el.loading=eager?'eager':'lazy';el.decoding='async';if(eager)el.fetchPriority='high';el.onerror=()=>el.remove();return el};
try{
const [response,manifest]=await Promise.all([fetch('editorial-feed.json',{cache:'no-store'}),fetch('editorial-images.json').then(r=>r.ok?r.json():[]).catch(()=>[])]);
if(!response.ok)throw Error('feed unavailable');
const feed=await response.json(),stories=Array.isArray(feed.articles)?feed.articles.slice(0,8):[],assets=manifest&&typeof manifest==='object'?manifest:{};
if(!stories.length){root.hidden=true;return}
root.textContent='';root.classList.add('rc-magazine');
const main=make('div','rc-mag-main'),side=make('aside','rc-mag-side');root.append(main,side);
const lead=stories[0],hero=make('a','rc-mag-hero');hero.href='noticias/'+encodeURIComponent(lead.id)+'/';
const leadImage=imagePath(lead,assets);if(assets.photos&&assets.photos[lead.id])hero.append(image(assets.photos[lead.id],'rc-mag-hero-image','Fotografia da matéria: '+lead.title,true));
const heroContent=make('div','rc-mag-hero-content');
heroContent.append(make('span','rc-mag-tag',lead.category||'Notícias'),make('h2','',lead.title),make('p','',lead.subtitle||'Confira os fatos e a análise completa.'));
heroContent.append(make('span','rc-mag-meta',formatDate(lead.date)+'  ·  '+readingTime(lead)+' min de leitura'));hero.append(heroContent);main.append(hero);
main.append(make('h2','rc-mag-section-title','ÚLTIMAS NOTÍCIAS'));
const list=make('div','rc-mag-list');main.append(list);
for(const a of stories.slice(1,6)){
 const link=make('a','rc-mag-item');link.href='noticias/'+encodeURIComponent(a.id)+'/';
 const tile=make('div','rc-mag-thumbnail'),asset=imagePath(a,assets);
 if(asset)tile.append(image(asset,'rc-mag-item-image','Arte editorial da matéria: '+a.title));
 else {tile.classList.add('rc-mag-thumbnail-empty');tile.textContent=(a.category||'RC').slice(0,2).toUpperCase();tile.setAttribute('aria-hidden','true')}
 const content=make('div','rc-mag-item-body');
 content.append(make('span','rc-mag-tag',a.category||'Análise'),make('h3','',a.title),make('p','',a.subtitle||'Leia a matéria completa.'),make('span','rc-mag-meta',formatDate(a.date)+'  ·  '+readingTime(a)+' min de leitura'));
 link.append(tile,content);list.append(link);
}
const existingAd=document.querySelector('.rc-home-columns .rc-ad-slot');if(existingAd)side.append(existingAd);
const popular=make('section','rc-mag-popular');popular.append(make('h2','rc-mag-section-title','EM ALTA'));
stories.slice(0,4).forEach((a,i)=>{const link=make('a','rc-mag-popular-item');link.href='noticias/'+encodeURIComponent(a.id)+'/';link.append(make('strong','',String(i+1)),make('span','',a.title));popular.append(link)});
side.append(popular);
const column=make('section','rc-mag-column');column.append(make('h2','rc-mag-section-title','COLUNA DO CORVO'));
const columnLink=make('a','rc-mag-column-link','Leia nossas análises e investigações');columnLink.href='coluna.html';column.append(columnLink);side.append(column);
}catch(error){root.textContent='';root.append(make('p','rc-mag-error','Não foi possível carregar as notícias agora.'))}
})();
