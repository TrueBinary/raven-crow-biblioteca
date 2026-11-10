"""Envia a newsletter pelo Buttondown: resumo diário das notícias e cada ensaio novo da Coluna.

Uso (no Actions, com BUTTONDOWN_API_KEY no ambiente):
  python newsletter_send.py resumo   # notícias de ontem (horário de Brasília)
  python newsletter_send.py coluna   # ensaios de hoje que ainda não foram enviados
O slug de cada e-mail (resumo-AAAA-MM-DD, coluna-<id>) é a trava contra envio duplicado.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SITE = "https://ravencrow.cloud"
API = "https://api.buttondown.com/v1"
BRT = timezone(timedelta(hours=-3))
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho",
         "agosto", "setembro", "outubro", "novembro", "dezembro"]
RODAPE = f"\n\n---\n\nMais em [ravencrow.cloud]({SITE}/)."


def _md(text: str) -> str:
    return re.sub(r"([\\\[\]*_`])", r"\\\1", str(text or "").strip())


def _data(day: str) -> str:
    y, m, d = map(int, day.split("-"))
    return f"{d} de {MESES[m - 1]} de {y}"


def _load(path: Path, key: str) -> list:
    return json.loads(path.read_text(encoding="utf-8")).get(key, []) if path.exists() else []


def digest(root: Path, day: str):
    """E-mail com as notícias publicadas em `day`; None se não houver nenhuma."""
    seen, items = set(), []
    for a in _load(root / "public/noticias.json", "articles") + _load(root / f"public/arquivo/noticias-{day}.json", "articles"):
        if a.get("date") == day and a.get("id") and a["id"] not in seen:
            seen.add(a["id"])
            items.append(a)
    if not items:
        return None
    lines = [f"As notícias do Raven Crow em {_data(day)}.\n"]
    for a in items:
        tag = f"{_md(a['category'])} · " if a.get("category") else ""
        lines.append(f"**[{_md(a.get('title'))}]({SITE}/noticias/{a['id']}/)**  \n{tag}{_md(a.get('subtitle'))}\n")
    return {"slug": f"resumo-{day}", "subject": f"O Corvo: as notícias de {_data(day)}", "body": "\n".join(lines) + RODAPE}


def columns(root: Path, day: str) -> list:
    """Um e-mail por ensaio da Coluna com data `day`, texto completo e link."""
    mails = []
    for e in _load(root / "public/coluna-ensaios.json", "essays"):
        if e.get("date") != day or not e.get("id"):
            continue
        url = f"{SITE}/coluna/{e['id']}/"
        body = "\n\n".join([f"*{_md(e.get('subtitle'))}*"] + [_md(p) for p in e.get("paragraphs", [])])
        body += f"\n\n[Ler no site, com fotos e fontes]({url})" + RODAPE
        slug = re.sub(r"[^a-zA-Z0-9_-]", "", f"coluna-{e['id']}")[:100]
        mails.append({"slug": slug, "subject": f"Coluna: {str(e.get('title', '')).strip()}", "body": body})
    return mails


def _api(method: str, path: str, body=None):
    req = urllib.request.Request(
        API + path if path.startswith("/") else path, method=method,
        data=json.dumps(body).encode() if body is not None else None,
        # Live-Dangerously: o Buttondown exige esse aceite para criar e-mail já em 'about_to_send' (envio automático escolhido).
        headers={"Authorization": f"Token {os.environ['BUTTONDOWN_API_KEY']}", "Content-Type": "application/json",
                 "X-Buttondown-Live-Dangerously": "true"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # O corpo do Buttondown traz code/detail (nunca a chave): sem ele o log só diz "400".
        sys.exit(f"Buttondown {method} {path}: HTTP {e.code} {e.read().decode(errors='replace')[:500]}")


def send(mails: list, api=_api) -> list:
    """Cria e envia os e-mails cujo slug ainda não existe no Buttondown; devolve os slugs enviados."""
    if not mails:
        return []
    existing, page = set(), api("GET", "/emails")
    for _ in range(5):  # shortcut: só as 5 páginas mais recentes; basta para o dia corrente
        existing |= {e.get("slug") for e in page.get("results", [])}
        if not page.get("next"):
            break
        page = api("GET", page["next"])
    sent = []
    for m in mails:
        if m["slug"] in existing:
            continue
        api("POST", "/emails", {**m, "status": "about_to_send"})
        sent.append(m["slug"])
    return sent


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if not os.environ.get("BUTTONDOWN_API_KEY"):
        print("BUTTONDOWN_API_KEY ausente: nada enviado.")
        sys.exit(0)
    root, today = Path(__file__).resolve().parent, datetime.now(BRT).date()
    if mode == "resumo":
        mails = [m for m in [digest(root, (today - timedelta(days=1)).isoformat())] if m]
    elif mode == "coluna":
        mails = columns(root, today.isoformat())
    else:
        sys.exit("uso: newsletter_send.py resumo|coluna")
    print("enviados:", send(mails) or "nenhum")
