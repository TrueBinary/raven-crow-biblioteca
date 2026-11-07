"""Synchronize Biblioteca do Corvo with the existing homepage book inventory.

Do not invent prices, editions, physical cover photos or availability.
The source-of-truth titles, authors and search URLs remain in index.html.
"""
from pathlib import Path
from html import escape
import json
import re

ROOT=Path(__file__).resolve().parent
PUBLIC=ROOT/'public'
home=(ROOT/'index.html').read_text(encoding='utf-8')
data_match=re.search(r'const books = (\[.*?\]);\s*function amazonUrl',home,re.S)
tag_match=re.search(r"const AMAZON_ASSOCIATE_TAG\s*=\s*'([^']*)';",home)
if not data_match or not tag_match:raise RuntimeError("Homepage book inventory unavailable")
inventory=json.loads(data_match.group(1))
ASSOCIATE_TAG=tag_match.group(1).strip()
WHY={
'olavo-jardim':"Para acompanhar diretamente a interpretação do autor sobre cultura e espiritualidade, identificando suas fontes, argumentos e pontos de contestação antes de formar uma opinião.",
'olavo-nova-era':"Para compreender como o autor aproxima debates filosóficos e disputas culturais e avaliar, com outras leituras, as conexões que ele propõe.",
'olavo-imbecil':"Para conhecer uma intervenção polêmica no debate intelectual brasileiro e refletir sobre a qualidade dos argumentos, o papel da crítica e seus limites.",
'tomas-reino':"Para examinar, a partir de um texto clássico, o bem comum, as virtudes do governante e os limites do poder, temas que continuam presentes em discussões sobre política.",
'tomas-suma':"Para ter uma obra de referência em filosofia e teologia sobre razão, fé, virtudes e justiça. É uma leitura de estudo, especialmente útil com a escolha cuidadosa do volume.",
'tomas-ente':"Para entrar na metafísica tomista por um texto relativamente breve e desenvolver um vocabulário mais rigoroso para discutir ser, essência e existência.",
'platao-apologia':"Para refletir sobre coragem intelectual, exame da própria vida e conflitos entre convicção e autoridade por meio de um diálogo fundador da filosofia ocidental.",
'platao-criton':"Para pensar o conflito entre obrigação legal e juízo de consciência, comparando os argumentos do diálogo com dilemas morais e jurídicos atuais.",
'platao-fedon':"Para acompanhar uma discussão filosófica sobre a alma, a morte e o sentido da vida examinada, distinguindo os argumentos de Platão de nossas próprias crenças.",
'platao-republica':"Para estudar as perguntas de Platão sobre justiça, educação, virtude e organização da cidade, mesmo quando se discorda de suas respostas políticas.",
'hoppe-democracia':"Para conhecer uma crítica controversa às instituições democráticas e examiná-la com argumentos contrários, distinguindo diagnóstico histórico, teoria e juízos normativos.",
'hoppe-socialismo':"Para comparar as categorias econômicas e os argumentos sobre propriedade e coordenação social apresentados por Hoppe com perspectivas econômicas alternativas.",
'hoppe-etica':"Para aprofundar uma defesa filosófica da propriedade privada e estudar seus pressupostos, objeções e implicações sem confundir a posição do autor com consenso acadêmico.",
'mises-seis-licoes':"Para conhecer de forma introdutória conceitos de mercado, moeda, inflação e intervenção estatal na tradição austríaca, complementando a leitura com outras escolas econômicas.",
'mises-acao-humana':"Para quem pretende estudar sistematicamente a argumentação de Mises sobre ação, preços e cálculo econômico; uma obra densa, mais indicada para leitura continuada."
}
CATS={'olavo':'Olavo de Carvalho','tomas':'São Tomás de Aquino','platao':'Platão e Sócrates','hoppe':'Hans-Hermann Hoppe','mises':'Ludwig von Mises'}
ids=set()
books=[]
for book in inventory:
    slug=book.get('id','')
    if not re.fullmatch(r'[a-z0-9-]+',slug) or slug in ids:raise ValueError("Invalid or duplicate book id")
    if slug not in WHY:raise ValueError("Add an editorial reason for book "+slug)
    if book.get('category') not in CATS:raise ValueError("Unknown category")
    ids.add(slug)
    books.append({**book,'whyRead':WHY[slug]})
payload={'schemaVersion':1,'source':'index.html — Biblioteca do Corvo','associateTag':ASSOCIATE_TAG,'books':books}
(PUBLIC/'livros.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
header_match=re.search(r'<header class="rc-global-header">.*?</header>',home,re.S)
if not header_match:raise ValueError("Shared header not found")
header=header_match.group(0)
noscript=''.join('<li><strong>'+escape(b['title'])+'</strong> — '+escape(b['author'])+': '+escape(b['description'])+'</li>' for b in books)
page='''<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="theme-color" content="#090a0c">
<title>Biblioteca do Corvo — Livros para pensar | Raven Crow</title>
<meta name="description" content="Conheça a curadoria do Raven Crow: filosofia, história das ideias, teologia e economia. Leia um resumo, descubra por que vale a leitura e consulte edições disponíveis.">
<meta property="og:type" content="website">
<meta property="og:title" content="Biblioteca do Corvo | Raven Crow">
<meta property="og:description" content="15 leituras selecionadas, com resumos e razões para ler cada obra.">
<link rel="canonical" href="https://ravencrow.cloud/livros.html">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=DM+Sans:wght@400;500;600;700;800&display=swap">
<link rel="stylesheet" href="raven-navigation.css"><link rel="stylesheet" href="raven-books.css">
<script defer src="raven-navigation.js"></script></head>
<body class="rc-books">'''+header+'''
<main id="main-content" class="rc-books-main">
<section class="rc-books-hero" aria-labelledby="book-title">
<p class="rc-books-eyebrow">RAVEN CROW / CURADORIA DE LEITURAS</p>
<h1 id="book-title">BIBLIOTECA <em>DO CORVO.</em></h1>
<p>Livros para ir além das manchetes: entenda as ideias, conheça seus autores e decida o que merece entrar na sua estante.</p>
<div class="rc-books-hero-meta"><strong id="book-count">'''+str(len(books))+''' livros selecionados</strong><span>Filosofia · Teologia · Economia · Debate intelectual</span></div>
</section>
<section class="rc-books-collection" aria-labelledby="books-heading">
<div class="rc-books-intro"><div><p class="rc-books-eyebrow">LEITURAS COM PROPÓSITO</p><h2 id="books-heading">O que ler — e por quê?</h2></div><p>Uma seleção comentada. Cada indicação explica o conteúdo e <strong>Por que vale a leitura</strong> de cada título, além de indicar onde consultar edições.</p></div>
<div class="rc-books-filters" role="group" aria-label="Filtrar livros por autor">
<button type="button" data-category="todos" aria-pressed="true">Todos</button>'''
for cat,author in CATS.items():
    page+='<button type="button" data-category="'+cat+'" aria-pressed="false">'+escape(author)+'</button>'
page+='''</div>
<div class="rc-books-list" id="book-grid" aria-live="polite"><p class="rc-books-loading">Carregando seleção...</p></div>
<noscript><ul class="rc-books-noscript">'''+noscript+'''</ul></noscript>
</section>
<section class="rc-books-next"><p class="rc-books-eyebrow">LEIA ANTES DE ESCOLHER</p><h2>Um livro não precisa confirmar o que você já pensa.</h2><p>Os autores desta lista têm perspectivas distintas e, em alguns casos, controversas. Compare interpretações, consulte o texto original e forme seu próprio juízo.</p>
<a href="coluna.html">Explore a Coluna do Corvo ↗</a></section>
<aside class="rc-books-disclosure" aria-label="Divulgação de afiliados"><h2>Divulgação de afiliados</h2>
<p>Os links levam a buscas de edições na Amazon Brasil e podem conter identificação de afiliado. O Raven Crow pode receber comissão em compras qualificadas. Os preços, formatos e estoques dependem da loja; confira a edição antes de comprar.</p>
<p>As recomendações são editoriais, não implicam concordância integral com os autores e não representam promessa de benefício financeiro ou pessoal.</p></aside>
</main><footer class="rc-books-footer">© Raven Crow · <a href="sobre.html">Sobre</a> · <a href="coluna.html">Coluna</a> · <a href="index.html">Início</a></footer>
<script defer src="raven-books.js"></script><script defer src="raven-analytics.js"></script>
</body></html>'''
(PUBLIC/'livros.html').write_text(page,encoding='utf-8')
from raven_seo import build as build_seo
build_seo(ROOT)
print('Imported',len(books),'books from homepage, built the independent catalogue page')
