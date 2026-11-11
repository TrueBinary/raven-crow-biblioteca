/* Biblioteca: the same 15 titles that appear in the site's homepage, enriched with a reason to read. */
(async function(){
const root=document.getElementById('book-grid');
if(!root)return;
// /en/library e /es/libros: livros.json traduzido ao lado da página (build-i18n-site.py).
const LANG=(document.documentElement.lang||'pt').slice(0,2).toLowerCase();
const t={pt:{stripe:'RAVEN CROW / LEITURA',why:'Por que vale a leitura',whyFallback:'Consulte o resumo e compare edições antes de decidir.',cta:'Consultar edições na Amazon ↗',aria:['Consultar edições de ',' na Amazon Brasil'],aff:'Link de afiliado · ver condições',ext:'Busca externa · preços não verificados',empty:'Não encontramos livros nessa categoria.',one:'livro selecionado',many:'livros selecionados',error:'A seleção de livros está temporariamente indisponível. Consulte a Biblioteca na página inicial.',back:'Abrir seleção da homepage',home:'/#biblioteca',labels:{olavo:'Olavo de Carvalho',tomas:'São Tomás de Aquino',platao:'Platão e Sócrates',hoppe:'Hans-Hermann Hoppe',mises:'Ludwig von Mises'}},
 en:{stripe:'RAVEN CROW / READING',why:"Why it's worth reading",whyFallback:'Read the summary and compare editions before deciding.',cta:'Find editions on Amazon Brazil ↗',aria:['Find editions of ',' on Amazon Brazil'],aff:'Affiliate link · see terms',ext:'External search · prices not verified',empty:'No books found in this category.',one:'book selected',many:'books selected',error:'The book selection is temporarily unavailable. See the Library on the home page.',back:'Open the home page selection',home:'/en/#biblioteca',labels:{olavo:'Olavo de Carvalho',tomas:'Thomas Aquinas',platao:'Plato and Socrates',hoppe:'Hans-Hermann Hoppe',mises:'Ludwig von Mises'}},
 es:{stripe:'RAVEN CROW / LECTURA',why:'Por qué vale la pena leerlo',whyFallback:'Consulta el resumen y compara ediciones antes de decidir.',cta:'Buscar ediciones en Amazon Brasil ↗',aria:['Buscar ediciones de ',' en Amazon Brasil'],aff:'Enlace de afiliado · ver condiciones',ext:'Búsqueda externa · precios no verificados',empty:'No encontramos libros en esta categoría.',one:'libro seleccionado',many:'libros seleccionados',error:'La selección de libros no está disponible por ahora. Consulta la Biblioteca en la página de inicio.',back:'Abrir la selección de la portada',home:'/es/#biblioteca',labels:{olavo:'Olavo de Carvalho',tomas:'Tomás de Aquino',platao:'Platón y Sócrates',hoppe:'Hans-Hermann Hoppe',mises:'Ludwig von Mises'}}}[LANG]||null;
if(!t)return;
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
 const labelMap=t.labels;
 function render(category='todos'){
  const selected=category==='todos'?books:books.filter(b=>b.category===category);
  root.replaceChildren();
  for(const book of selected){
   const article=make('article','rc-book');
   const cover=make('div','rc-book-cover');
   cover.style.setProperty('--cover-color',/^#[0-9a-fA-F]{6}$/.test(book.color||'')?book.color:'#a75d58');
   cover.setAttribute('aria-hidden','true');
   cover.append(make('span','rc-book-cover-stripe',t.stripe),make('strong','',book.title),make('span','rc-book-cover-author',book.author));
   const body=make('div','rc-book-content');
   body.append(make('div','rc-book-category',labelMap[book.category]||book.author));
   body.append(make('h3','',book.title),make('p','rc-book-author',book.author),make('p','rc-book-description',book.description));
   const why=make('section','rc-book-reason');
   why.append(make('h4','',t.why),make('p','',book.whyRead||t.whyFallback));
   body.append(why);
   const meta=make('div','rc-book-bottom');
   const link=make('a','rc-book-cta',t.cta);
   link.href=amazonUrl(book);link.target='_blank';link.rel='noopener noreferrer sponsored';
   link.setAttribute('aria-label',t.aria[0]+book.title+t.aria[1]);
   link.dataset.track='library';link.dataset.placement='livros-catalogo';
   const note=make('small','rc-book-affiliate',associateTag?t.aff:t.ext);
   meta.append(link,note);body.append(meta);article.append(cover,body);root.append(article);
  }
  if(!selected.length)root.append(make('p','rc-book-empty',t.empty));
  if(count)count.textContent=selected.length+' '+(selected.length===1?t.one:t.many);
  buttons.forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.category===category)));
 }
 buttons.forEach(button=>button.addEventListener('click',()=>render(button.dataset.category)));
 render();
}catch(error){
 root.replaceChildren(make('p','rc-book-empty',t.error));
 const a=make('a','rc-book-back',t.back);a.href=t.home;root.append(a);
}
})();
