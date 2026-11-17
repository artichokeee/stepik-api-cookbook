#!/usr/bin/env python3
"""Выгрузить свой курс Stepik в один JSON: модули, уроки, шаги вместе с block.

Только чтение. В файл попадают и правильные ответы заданий (block.source),
поэтому храните копию так же бережно, как сам курс.

    export STEPIK_CLIENT_ID=... STEPIK_CLIENT_SECRET=...
    python3 backup_course.py COURSE_ID [OUT.json]

License: MIT, (c) 2026 Artsiom Rusau.
"""
import json
import os
import random
import sys
import time

import requests

API = "https://stepik.org/api"
TOKEN_URL = "https://stepik.org/oauth2/token/"
PAUSE = 0.35      # секунд между запросами
BATCH = 30        # id в одном запросе ids[]


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
    """Один запрос: пауза, до 2 повторов на 429/5xx и обрыв связи, стоп на блокировке."""
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
    """Объекты по списку id, пачками по 30. Недоступные Stepik молча не возвращает."""
    ids = list(dict.fromkeys(i for i in ids if i))
    out = []
    for i in range(0, len(ids), BATCH):
        chunk = ids[i:i + BATCH]
        out += call(s, "GET", f"/{resource}", params={"ids[]": chunk})[resource]
    missing = set(ids) - {o["id"] for o in out}
    if missing:
        print(f"  {resource}: не получено {len(missing)} из {len(ids)} (нет доступа или удалены)", file=sys.stderr)
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    course_id = int(sys.argv[1])
    out_path = sys.argv[2] if len(sys.argv) > 2 else f"course-{course_id}-backup.json"

    s = session()
    found = call(s, "GET", f"/courses/{course_id}")["courses"]
    if not found:
        sys.exit(f"Курс {course_id} не найден или недоступен.")
    course = found[0]

    # sections?course= возвращает пустой список, поэтому модули читаются по id
    sections = sorted(by_ids(s, "sections", course.get("sections") or []), key=lambda x: x["position"])
    units = by_ids(s, "units", [u for sec in sections for u in sec.get("units") or []])
    lessons = {l["id"]: l for l in by_ids(s, "lessons", [u["lesson"] for u in units])}
    step_ids = [st for l in lessons.values() for st in l.get("steps") or []]
    steps = {st["id"]: st for st in by_ids(s, "step-sources", step_ids)}

    units_by_section = {}
    for u in units:
        units_by_section.setdefault(u["section"], []).append(u)

    tree = []
    for sec in sections:
        items = []
        for u in sorted(units_by_section.get(sec["id"], []), key=lambda x: x["position"]):
            lesson = lessons.get(u["lesson"])
            if not lesson:
                continue
            items.append({
                "unit": u,
                "lesson": lesson,
                "steps": [steps[i] for i in lesson.get("steps") or [] if i in steps],
            })
        tree.append({"section": sec, "lessons": items})

    data = {"saved_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "course": course, "sections": tree}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Сохранено: {out_path} – модулей {len(sections)}, уроков {len(lessons)}, шагов {len(steps)}")


if __name__ == "__main__":
    main()
