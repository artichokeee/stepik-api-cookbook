#!/usr/bin/env python3
"""Заменить текст одного текстового шага содержимым HTML-файла.

Без --apply ничего не пишет: показывает, что изменится. С --apply сначала
сохраняет прежний шаг в step-<id>-backup.json, потом отправляет PUT полным
объектом и читает шаг обратно.

    export STEPIK_CLIENT_ID=... STEPIK_CLIENT_SECRET=...
    python3 update_text_step.py STEP_ID new_text.html           # пробный прогон
    python3 update_text_step.py STEP_ID new_text.html --apply   # запись

License: MIT, (c) 2026 Artsiom Rusau.
"""
import argparse
import json
import os
import random
import sys
import time

import requests

API = "https://stepik.org/api"
TOKEN_URL = "https://stepik.org/oauth2/token/"
PAUSE = 0.35
# Поля шага, которые лежат рядом с block и отправляются обратно без изменений.
STEP_FIELDS = ("lesson", "position", "cost", "max_submissions_count", "has_submissions_restrictions")


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


def main():
    p = argparse.ArgumentParser(description="Новый текст для текстового шага Stepik.")
    p.add_argument("step_id", type=int)
    p.add_argument("html_file")
    p.add_argument("--apply", action="store_true", help="записать в Stepik (без флага – только показать)")
    a = p.parse_args()

    with open(a.html_file, encoding="utf-8") as f:
        new_text = f.read().strip()
    if not new_text:
        sys.exit("Файл пустой – пустой шаг записывать не буду.")

    s = session()
    found = call(s, "GET", f"/step-sources/{a.step_id}")["step-sources"]
    if not found:
        sys.exit(f"Шаг {a.step_id} не найден или нет прав автора.")
    step = found[0]
    block = step.get("block") or {}
    if block.get("name") != "text":
        sys.exit(f"Шаг {a.step_id} типа {block.get('name')!r}, а скрипт правит только text: "
                 "у заданий в block обязателен полный source.")

    old_text = block.get("text") or ""
    print(f"Шаг {a.step_id}, урок {step['lesson']}, позиция {step['position']}")
    print(f"  было символов: {len(old_text)}, станет: {len(new_text)}")
    if old_text == new_text:
        print("  Текст совпадает – писать нечего.")
        return
    if not a.apply:
        print("  Пробный прогон: ничего не записано. Добавьте --apply, чтобы записать.")
        return

    backup = f"step-{a.step_id}-backup.json"
    with open(backup, "w", encoding="utf-8") as f:
        json.dump(step, f, ensure_ascii=False, indent=2)
    print(f"  прежний шаг сохранен: {backup}")

    # PUT – полным объектом: block целиком плюс поля шага, прочитанные выше
    payload = {k: step[k] for k in STEP_FIELDS if k in step}
    payload["block"] = dict(block, text=new_text)
    call(s, "PUT", f"/step-sources/{a.step_id}", json={"stepSource": payload})

    back = call(s, "GET", f"/step-sources/{a.step_id}")["step-sources"][0]["block"].get("text") or ""
    if back == new_text:
        print("  Записано, текст совпадает с файлом.")
    else:
        # Обычно это работа санитайзера: часть стилей и атрибутов Stepik вырезает.
        print(f"  Записано, но Stepik вернул текст иначе ({len(back)} символов): "
              "проверьте стили и разметку, см. docs/05-step-types.md, раздел про санитайзер.")


if __name__ == "__main__":
    main()
