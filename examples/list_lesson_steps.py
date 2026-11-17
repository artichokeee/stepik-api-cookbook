#!/usr/bin/env python3
"""Показать шаги урока: позиция, id, тип, начало текста и статус сборки.

Только чтение. Статус (ready/error) и причина ошибки берутся из /api/steps:
в /api/step-sources этих полей нет.

    export STEPIK_CLIENT_ID=... STEPIK_CLIENT_SECRET=...
    python3 list_lesson_steps.py LESSON_ID

License: MIT, (c) 2026 Artsiom Rusau.
"""
import html
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
    out = []
    for i in range(0, len(ids), BATCH):
        out += call(s, "GET", f"/{resource}", params={"ids[]": ids[i:i + BATCH]})[resource]
    return out


def preview(block, width=60):
    text = re.sub(r"<[^>]+>", " ", block.get("text") or "")
    text = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return text[:width] + ("…" if len(text) > width else "")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    lesson_id = int(sys.argv[1])
    s = session()

    found = call(s, "GET", f"/lessons/{lesson_id}")["lessons"]
    if not found:
        sys.exit(f"Урок {lesson_id} не найден или недоступен.")
    lesson = found[0]
    ids = lesson.get("steps") or []
    print(f"Урок {lesson_id}: {lesson['title']}  (is_public={lesson.get('is_public')}, шагов {len(ids)})")
    if lesson.get("is_public"):
        print("  Внимание: урок публичный – открывается по прямой ссылке любому.")

    sources = {x["id"]: x for x in by_ids(s, "step-sources", ids)}
    states = {x["id"]: x for x in by_ids(s, "steps", ids)}

    for sid in ids:
        src = sources.get(sid)
        if not src:
            print(f"  ?  {sid}: нет доступа к step-sources")
            continue
        block = src.get("block") or {}
        st = states.get(sid, {})
        status = st.get("status") or "-"
        print(f"  {src['position']:>2}  {sid:<10} {block.get('name', '?'):<13} {status:<6} {preview(block)}")
        if status == "error":
            print(f"      причина: {st.get('reason_of_failure')}")


if __name__ == "__main__":
    main()
