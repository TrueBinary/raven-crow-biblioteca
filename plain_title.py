"""Título em CAIXA ALTA -> caixa normal para <title>, og:title, headline e sitemap (buscadores e IAs citam o texto como está).

Não dá para adivinhar nome próprio: cada palavra copia a forma com que aparece no texto da própria matéria
(ou, se não aparece lá, no texto das outras matérias). Aparece minúscula em algum lugar -> palavra comum;
senão usa a forma mais comum (PRF, JPMorgan, Consciência). Começo de frase não conta, porque ali tudo é maiúsculo.
Pares contam antes de palavras soltas: "União Europeia" e "Série A" mesmo que "europeia" apareça minúscula noutro lugar.
"""
import re
from collections import Counter
from functools import lru_cache

WORD = re.compile(r"[^\W\d_]+")
TEXT_FIELDS = ("subtitle", "facts", "analysis", "counterpoint")


def article_text(d: dict) -> str:
    """Texto de uma matéria (ou do bloco en/es dela) para servir de referência de maiúsculas."""
    return "\n".join(str(d.get(k) or "") for k in TEXT_FIELDS)


@lru_cache(maxsize=8)  # o corpus de todas as matérias é o mesmo texto a cada chamada
def _forms(text: str):
    """uni[palavra], bi[(anterior, palavra)] = formas da palavra; nxt[(palavra, seguinte)] = formas da palavra."""
    uni: dict[str, Counter] = {}
    bi: dict[tuple, Counter] = {}
    nxt: dict[tuple, Counter] = {}
    acro: dict[str, Counter] = {}  # siglas e formas mistas (GTA, JPMorgan) valem mesmo em começo de frase
    prev, prev_end, prev_start = None, 0, True
    for m in WORD.finditer(text):
        w = m.group(0)
        gap = text[prev_end:m.start()]
        start = prev is None or bool(re.search(r"[.!?:;\n]", gap))
        if not w.islower() and not (w.istitle() and len(w) > 1) and len(w) > 1:
            acro.setdefault(w.lower(), Counter())[w] += 1
        if prev is not None and gap.strip() == "" and not start:
            bi.setdefault((prev.lower(), w.lower()), Counter())[w] += 1
            if not prev_start:
                nxt.setdefault((prev.lower(), w.lower()), Counter())[prev] += 1
        if not start:
            uni.setdefault(w.lower(), Counter())[w] += 1
        prev, prev_end, prev_start = w, m.end(), start
    return uni, bi, nxt, acro


def _pick(forms: Counter | None):
    if not forms:
        return None
    if any(f.islower() for f in forms):
        return "lower"
    return forms.most_common(1)[0][0]


def plain_title(title: str, context: str = "", corpus: str = "") -> str:
    if not title or not title.isupper():
        return title
    tables = [_forms(context), _forms(corpus) if corpus else ({}, {}, {}, {})]
    words = list(WORD.finditer(title))
    joined = lambda a, b: title[words[a].end():words[b].start()].strip() == ""
    out, last = [], 0
    for i, m in enumerate(words):
        low = m.group(0).lower()
        pair = (words[i - 1].group(0).lower(), low) if i and joined(i - 1, i) else None
        ahead = (low, words[i + 1].group(0).lower()) if i + 1 < len(words) and joined(i, i + 1) else None
        def by_pair(uni, bi, nxt, acro):
            got = [f for f in (_pick(nxt.get(ahead)), _pick(bi.get(pair))) if f]
            # um par com maiúscula ("Série A", "União Europeia") vence o outro par em minúscula
            return next((f for f in got if f != "lower"), got[0] if got else None)

        form = next((f for t in tables for f in (by_pair(*t), _pick(t[0].get(low)), _pick(t[3].get(low))) if f), None)
        if form is None:
            # não aparece em lugar nenhum: colada a número é código (PS5, G20) e fica como está
            near_digit = title[m.end():m.end() + 1].isdigit() or title[max(0, m.start() - 1):m.start()].isdigit()
            form = m.group(0) if near_digit else "lower"
        out.append(title[last:m.start()] + (low if form == "lower" else form))
        last = m.end()
    res = "".join(out) + title[last:]
    i = next((k for k, c in enumerate(res) if c.isalpha()), None)
    return res if i is None else res[:i] + res[i].upper() + res[i + 1:]
