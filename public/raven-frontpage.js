/* Editorial homepage: render only documented stories from the existing feed. */
(async()=>{
const root=document.querySelector('#editorial-feed');if(!root)return;
try{
const r=await fetch('noticias.json',{cache:'no-store'});if(!r.ok)throw Error('feed');
const data=await r.json();const articles=Array.isArray(data.articles)?data.articles.slice(0,4):[];
if(!articles.length){root.hidden=true;return}
const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n};
const label=el('p','editorial-label','RAVEN CROW  /  ÚLTIMAS INVESTIGAÇÕES');
root.append(label);
const grid=el('div','editorial-grid');root.append(grid);
for(const [i,a] of articles.entries()){
const link=el('a','editorial-story'+(i===0?' editorial-lead':''));
link.href='noticias/'+encodeURIComponent(a.id)+'/';
link.append(el('span','editorial-category',a.category||'ANÁLISE'));
link.append(el('h2','',a.title));
link.append(el('p','',a.subtitle||'Leia a análise completa, as fontes e o contraponto.'));
link.append(el('span','editorial-more','LER ANÁLISE  ↗'));
grid.append(link);
}
}catch(e){root.hidden=true}
})();