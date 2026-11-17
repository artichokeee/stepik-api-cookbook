#!/usr/bin/env python3
"""Найти строку или регулярное выражение во всех шагах своего курса.

Только чтение: ничего не меняет. Ищет в тексте шага (block.text) и в настройках
задания (block.source), печатает урок, позицию шага, ссылку и кусок вокруг находки.

    export STEPIK_CLIENT_ID=... STEPIK_CLIENT_SECRET=...
    python3 find_in_steps.py COURSE_ID "ucarecdn.com"
    python3 find_in_steps.py COURSE_ID "margin-left\\s*:" --regex --ignore-case

License: MIT, (c) 2026 Artsiom Rusau.
"""
import argparse
import json
import os
import random
import re
import sys
import time

import requests

API = "https://stepik.org/api"
TOKEN_URL = "https://stepik.org/oauth2/token/"
PAUSE = 0.35
BATCH = 30


def session():
    cid = os.environ.get("STEPIK_CLIENT_ID")
    secret = os.environ.get("STEPIK_CLIENT_SECRET")
    if not cid or not secret:
        sys.exit("Задайте STEPIK_CLIENT_ID и STEPIK_CLIENT_SECRET в окружении.")
    r = requests.post(TOKEN_URL, data={"grant_type": "client_credentials"},
                      auth=(cid, secret), timeout=20)
    if r.status_code != 200:
        sys.exit(f"Токен не получен: {r.status_code} {r.text[:200]}")
    s = requests.Session()
    s.headers["Authorization"] = "Bearer " + r.json()["access_token"]
    return s


def call(s, method, path, **kw):
    url = API + path
    for attempt in range(3):
        time.sleep(PAUSE)
        try:
            r = s.request(method, url, timeout=30, **kw)
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)
            continue
        if (r.status_code == 429 or r.status_code >= 500) and attempt < 2:
            time.sleep(1.5 * 4 ** attempt + random.random() * 0.5)
            continue
        if r.status_code == 403 and "json" not in r.headers.get("content-type", ""):
            sys.exit("403 от защиты Stepik, а не от API. Остановитесь на 5-10 минут и не повторяйте запрос.")
        if not r.ok:
            sys.exit(f"{method} {path} -> {r.status_code}: {r.text[:300]}")
        return r.json() if r.text else None
    return None


def by_ids(s, resource, ids):
    ids = list(dict.fromkeys(i for i in ids if i))
    out = []
    for i in range(0, len(ids), BATCH):
        out += call(s, "GET", f"/{resource}", params={"ids[]": ids[i:i + BATCH]})[resource]
    return out


def snippets(text, rx, width=50):
    for m in rx.finditer(text):
        a, b = max(0, m.start() - width), min(len(text), m.end() + width)
        yield text[a:b].replace("\n", " ")


def main():
    p = argparse.ArgumentParser(description="Поиск по шагам своего курса (только чтение).")
    p.add_argument("course_id", type=int)
    p.add_argument("pattern")
    p.add_argument("--regex", action="store_true", help="считать образец регулярным выражением")
    p.add_argument("--ignore-case", action="store_true")
    a = p.parse_args()

    flags = re.IGNORECASE if a.ignore_case else 0
    rx = re.compile(a.pattern if a.regex else re.escape(a.pattern), flags)

    s = session()
    found = call(s, "GET", f"/courses/{a.course_id}")["courses"]
    if not found:
        sys.exit(f"Курс {a.course_id} не найден или недоступен.")
    course = found[0]

    sections = by_ids(s, "sections", course.get("sections") or [])
    units = by_ids(s, "units", [u for sec in sections for u in sec.get("units") or []])
    lessons = by_ids(s, "lessons", [u["lesson"] for u in units])
    title = {l["id"]: l["title"] for l in lessons}
    steps = by_ids(s, "step-sources", [st for l in lessons for st in l.get("steps") or []])

    hits = 0
    for st in sorted(steps, key=lambda x: (x["lesson"], x["position"])):
        block = st.get("block") or {}
        parts = [("text", block.get("text") or "")]
        if block.get("source"):
            parts.append(("source", json.dumps(block["source"], ensure_ascii=False)))
        for where, text in parts:
            for snip in snippets(text, rx):
                hits += 1
                print(f"{title.get(st['lesson'], st['lesson'])} / шаг {st['position']} [{block.get('name')}, {where}]")
                print(f"  https://stepik.org/lesson/{st['lesson']}/step/{st['position']}")
                print(f"  …{snip}…")
    print(f"\nНайдено: {hits} (шагов просмотрено: {len(steps)})")


if __name__ == "__main__":
    main()
