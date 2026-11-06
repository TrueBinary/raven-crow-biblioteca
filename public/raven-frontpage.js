/* Raven Crow: news-first magazine layout. All headlines come from the published feed. */
(async function(){
const root=document.getElementById('editorial-feed');if(!root)return;
const make=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!=null)e.textContent=txt;return e};
try{
const response=await fetch('noticias.json',{cache:'no-store'});if(!response.ok)throw Error('feed unavailable');
const feed=await response.json(),stories=Array.isArray(feed.articles)?feed.articles.slice(0,8):[];
if(!stories.length){root.hidden=true;return}
root.textContent='';root.classList.add('rc-magazine');
const main=make('div','rc-mag-main'),side=make('aside','rc-mag-side');
root.append(main,side);
const lead=stories[0],hero=make('a','rc-mag-hero');
hero.href='noticias/'+encodeURIComponent(lead.id)+'/';
hero.append(make('span','rc-mag-tag',lead.category||'Notícias'),make('h2','',lead.title),make('p','',lead.subtitle||'Confira os fatos e a análise completa.'));
const meta=make('span','rc-mag-meta',lead.date||'Raven Crow');hero.append(meta);main.append(hero);
const heading=make('h2','rc-mag-section-title','ÚLTIMAS NOTÍCIAS');main.append(heading);
const list=make('div','rc-mag-list');main.append(list);
for(const a of stories.slice(1,6)){
 const link=make('a','rc-mag-item');link.href='noticias/'+encodeURIComponent(a.id)+'/';
 const tile=make('div','rc-mag-thumbnail');tile.setAttribute('aria-hidden','true');tile.textContent=(a.category||'RC').slice(0,2).toUpperCase();
 const content=make('div','rc-mag-item-body');content.append(make('span','rc-mag-tag',a.category||'Análise'),make('h3','',a.title),make('p','',a.subtitle||'Leia a matéria completa.'),make('span','rc-mag-meta',a.date||'Raven Crow'));
 link.append(tile,content);list.append(link);
}
const existingAd=document.querySelector('.rc-home-columns .rc-ad-slot');if(existingAd)side.append(existingAd);
const popular=make('section','rc-mag-popular');popular.append(make('h2','rc-mag-section-title','EM ALTA'));
stories.slice(0,4).forEach((a,i)=>{const link=make('a','rc-mag-popular-item');link.href='noticias/'+encodeURIComponent(a.id)+'/';link.append(make('strong','',String(i+1)),make('span','',a.title));popular.append(link)});
side.append(popular);
const column=make('section','rc-mag-column');column.append(make('h2','rc-mag-section-title','COLUNA DO CORVO'));
const columnLink=make('a','rc-mag-column-link','Leia nossas análises e investigações');columnLink.href='noticias.html';column.append(columnLink);side.append(column);
}catch(error){root.textContent='';root.append(make('p','rc-mag-error','Não foi possível carregar as notícias agora.')); }
})();
