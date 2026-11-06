/* Biblioteca: the same 15 titles that appear in the site's homepage, enriched with a reason to read. */
(async function(){
const root=document.getElementById('book-grid');
if(!root)return;
const count=document.getElementById('book-count');
const buttons=[...document.querySelectorAll('.rc-books-filters button')];
const make=(tag,cls,content)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(content!==undefined)e.textContent=content;return e};
try{
 const response=await fetch('livros.json',{cache:'no-store'});
 if(!response.ok)throw Error('library unavailable');
 const feed=await response.json();
 const books=Array.isArray(feed.books)?feed.books:[];
 const associateTag=typeof feed.associateTag==='string'?feed.associateTag.trim():'';
 const amazonUrl=(book)=>{
  const url=new URL('https://www.amazon.com.br/s');
  const params=new URLSearchParams({k:book.query||book.title+' '+book.author});
  if(associateTag)params.set('tag',associateTag);
  url.search=params.toString();
  return url.href;
 };
 const labelMap={olavo:'Olavo de Carvalho',tomas:'São Tomás de Aquino',platao:'Platão e Sócrates',hoppe:'Hans-Hermann Hoppe',mises:'Ludwig von Mises'};
 function render(category='todos'){
  const selected=category==='todos'?books:books.filter(b=>b.category===category);
  root.replaceChildren();
  for(const book of selected){
   const article=make('article','rc-book');
   const cover=make('div','rc-book-cover');
   cover.style.setProperty('--cover-color',/^#[0-9a-fA-F]{6}$/.test(book.color||'')?book.color:'#a75d58');
   cover.setAttribute('aria-hidden','true');
   cover.append(make('span','rc-book-cover-stripe','RAVEN CROW / LEITURA'),make('strong','',book.title),make('span','rc-book-cover-author',book.author));
   const body=make('div','rc-book-content');
   body.append(make('div','rc-book-category',labelMap[book.category]||book.author));
   body.append(make('h3','',book.title),make('p','rc-book-author',book.author),make('p','rc-book-description',book.description));
   const why=make('section','rc-book-reason');
   why.append(make('h4','','Por que vale a leitura'),make('p','',book.whyRead||'Consulte o resumo e compare edições antes de decidir.'));
   body.append(why);
   const meta=make('div','rc-book-bottom');
   const link=make('a','rc-book-cta','Consultar edições na Amazon ↗');
   link.href=amazonUrl(book);link.target='_blank';link.rel='noopener noreferrer sponsored';
   link.setAttribute('aria-label','Consultar edições de '+book.title+' na Amazon Brasil');
   link.dataset.track='library';link.dataset.placement='livros-catalogo';
   const note=make('small','rc-book-affiliate',associateTag?'Link de afiliado · ver condições':'Busca externa · preços não verificados');
   meta.append(link,note);body.append(meta);article.append(cover,body);root.append(article);
  }
  if(!selected.length)root.append(make('p','rc-book-empty','Não encontramos livros nessa categoria.'));
  if(count)count.textContent=selected.length+' '+(selected.length===1?'livro selecionado':'livros selecionados');
  buttons.forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.category===category)));
 }
 buttons.forEach(button=>button.addEventListener('click',()=>render(button.dataset.category)));
 render();
}catch(error){
 root.replaceChildren(make('p','rc-book-empty','A seleção de livros está temporariamente indisponível. Consulte a Biblioteca na página inicial.'));
 const a=make('a','rc-book-back','Abrir seleção da homepage');a.href='index.html#biblioteca';root.append(a);
}
})();
