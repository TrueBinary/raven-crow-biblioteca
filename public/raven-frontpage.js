/* Editorial homepage: render only documented stories from the existing feed. */
(async()=>{
const root=document.querySelector('#editorial-feed');if(!root)return;
try{
const r=await fetch('noticias.json',{cache:'no-store'});if(!r.ok)throw Error('feed');
const data=await r.json();const articles=Array.isArray(data.articles)?data.articles.slice(0,4):[];
if(!articles.length){root.hidden=true;return}
const el=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n};
// mesma regra de public/noticias.html: palavra antes do ":"/"?" em vermelho, resto do título como linha menor
const titleEl=t=>{const h=el('h2'),m=t.match(/^(.+?[:?])\s*(.*)$/),head=m?m[1].replace(/:$/,''):t,rest=m?m[2]:'',i=head.lastIndexOf(' ');
 if(i>0)h.append(head.slice(0,i+1));h.append(el('em','',i>0?head.slice(i+1):head));if(rest)h.append(el('span','rc-h1-sub',rest));return h};
const label=el('p','editorial-label','RAVEN CROW  /  ÚLTIMAS INVESTIGAÇÕES');
root.append(label);
const grid=el('div','editorial-grid');root.append(grid);
for(const [i,a] of articles.entries()){
const link=el('a','editorial-story'+(i===0?' editorial-lead':''));
link.href='noticias/'+encodeURIComponent(a.id)+'/';
link.append(el('span','editorial-category',a.category||'ANÁLISE'));
link.append(titleEl(String(a.title||'')));
link.append(el('p','',a.subtitle||'Leia a análise completa, as fontes e o contraponto.'));
link.append(el('span','editorial-more','LEIA A ANÁLISE COMPLETA →'));
grid.append(link);
}
}catch(e){root.hidden=true}
})();