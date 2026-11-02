from pathlib import Path
root=Path(__file__).resolve().parent
pages=[root/'index.html',root/'public/noticias.html',*sorted((root/'public/noticias').glob('*/index.html'))]
for p in pages:
    if not p.is_file(): continue
    css='../../raven-editorial.css' if p.parent.parent.name=='noticias' else 'raven-editorial.css'
    tag=f'<link rel="stylesheet" href="{css}">'
    s=p.read_text(encoding='utf-8')
    if tag not in s:
        s=s.replace('</head>',tag+'</head>',1)
        p.write_text(s,encoding='utf-8')
        print('THEMED',p.relative_to(root))
