"""Move de public/noticias.json para public/arquivo/noticias-<data>.json as matérias com mais de KEEP_DAYS dias.

A API de conteúdo do GitHub devolve conteúdo vazio acima de 1 MB, e o Corvo Investigador (ChatGPT) lê e grava
este arquivo inteiro. O site já junta noticias.json com arquivo/*.json (build-raven.py, raven_seo.py): nada some.
"""
from __future__ import annotations

import copy
import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KEEP_DAYS = 2
# Brasil sem horário de verão desde 2019: -03:00 fixo evita depender do pacote tzdata no Windows.
BRT = timezone(timedelta(hours=-3))
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _day(article: dict) -> date | None:
    d = article.get("date")
    if not isinstance(d, str) or not ISO.match(d):
        return None
    try:
        return date.fromisoformat(d)
    except ValueError:
        return None


def _new_edition(news: dict, day: date) -> dict:
    return {"schemaVersion": news.get("schemaVersion", 1), "editorial": news.get("editorial"),
            "edition": day.strftime("%d/%m/%Y"), "updatedAt": news.get("updatedAt"),
            "tz": news.get("tz"), "articles": []}


def rotate(news: dict, archive: dict[str, dict], today: date, keep_days: int = KEEP_DAYS) -> tuple[dict, dict[str, dict]]:
    """Devolve o novo noticias.json e só os arquivos de `archive` que mudaram ou foram criados."""
    cutoff = today - timedelta(days=keep_days - 1)
    keep, move = [], []
    for a in news["articles"]:
        d = _day(a)
        (move if d and d < cutoff else keep).append(a)
    if not move:
        return news, {}

    where: dict[str, set[str]] = {}
    for name, ed in archive.items():
        for a in ed.get("articles", []):
            where.setdefault(a.get("id"), set()).add(name)

    out: dict[str, dict] = {}
    for a in move:
        target = f"noticias-{a['date']}.json"
        for name in where.get(a["id"], set()) | {target}:
            if name not in out:
                out[name] = copy.deepcopy(archive[name]) if name in archive else _new_edition(news, _day(a))
            arts = out[name]["articles"]
            # a versão de noticias.json é a mais nova: substitui a cópia velha de snapshots anteriores
            arts[:] = [x for x in arts if x.get("id") != a["id"]] + [a]

    for name, ed in out.items():
        ed["articles"].sort(key=lambda x: x.get("date") or "", reverse=True)
    changed = {name: ed for name, ed in out.items() if archive.get(name) != ed}
    return {**news, "articles": keep}, changed


def _dump(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def _write_if_changed(path: Path, obj: dict) -> None:
    text = _dump(obj)
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def main(root: Path = ROOT, today: date | None = None) -> int:
    pub = root / "public"
    path = pub / "noticias.json"
    news = json.loads(path.read_text(encoding="utf-8"))
    archive = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in sorted((pub / "arquivo").glob("noticias-*.json"))}
    new, changed = rotate(news, archive, today or datetime.now(BRT).date())
    # arquivo antes de noticias.json: se cair no meio, a matéria fica duplicada, nunca perdida
    for name, ed in changed.items():
        _write_if_changed(pub / "arquivo" / name, ed)
    if new is not news:
        _write_if_changed(path, new)
    return len(news["articles"]) - len(new["articles"])


if __name__ == "__main__":
    print(f"rotate-news: {main()} matérias movidas")
