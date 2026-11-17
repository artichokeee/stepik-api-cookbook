# Stepik API cookbook

Practical notes on the undocumented Stepik API (stepik.org/api) for course authors: authentication, course structure, reading and writing lessons and steps, step block formats, media, comments, announcements, errors and permissions. Every quirk here was found on a live course and is written as "what you expect → what really happens → what to do". The text is in Russian; code and field names are kept exactly as the API uses them.

---

Практические заметки по API Stepik для авторов курсов. Официальной документации у API почти нет: формат шагов, обязательные поля, фильтры, которые молча ничего не находят, – все это приходится выяснять на живом курсе. Здесь собрано то, что уже выяснено.

Автор – Артем Русов (Artyom Rusau), автор курсов на Stepik.

## Для кого

Для автора или соавтора курса на Stepik, который хочет делать скриптом то, что долго делать руками в редакторе: выгрузить курс в JSON, найти фразу во всех шагах, поправить текст шага, расставить модули по порядку, ответить на комментарии в своем курсе.

Программировать для этого не нужно. Готовые скрипты из [examples/](examples/) запускаются одной командой, а [пошаговая инструкция](#первый-запуск-без-опыта-программирования) ниже рассказывает, что установить и что делать, если сразу не заработало.

Это неофициальное руководство, оно не связано с командой Stepik. Stepik – товарный знак его владельцев. Официальные материалы: список методов [stepik.org/api/docs](https://stepik.org/api/docs) и примеры [StepicOrg/Stepik-API](https://github.com/StepicOrg/Stepik-API). Stepik может поменять поведение API в любой день; где известна дата проверки, она указана.

Все примеры работают с вашим собственным курсом через ваше OAuth-приложение и бережно относятся к серверу: запросы идут последовательно и с паузой.

## Пять фактов, которые стоит знать до первого запроса

1. **У API нет CORS.** Из браузера его не вызвать – только из скрипта или своего сервера.
2. **Обновление – это `PUT` полным объектом.** Частичного `PATCH` нет; у курса и урока без `title` запрос отбивается с 400.
3. **Урок, созданный через API, по умолчанию публичный** – открывается по прямой ссылке кому угодно. Передавайте `is_public: false` явно.
4. **HTML в `POST /api/courses` блокирует защита Stepik**, а серия таких запросов закрывает доступ с вашего IP на 5–10 минут. Увидели 403 с HTML-страницей вместо JSON – остановитесь и не повторяйте запрос.
5. **201 на создание исполняемого шага (`code`, `sql`, `math`…) не значит, что шаг работает.** Stepik собирает его через несколько секунд и может пометить `status: "error"`.

## Первый запуск без опыта программирования

Понадобятся Python, одна библиотека и командная строка. Редактор кода не обязателен: скрипты запускаются из командной строки и ничего не нужно в них править.

### 1. Установите Python 3

- **Windows.** Скачайте установщик с [python.org/downloads](https://www.python.org/downloads/). В первом окне установщика поставьте галочку **"Add python.exe to PATH"** – без нее команда `python` не найдется.
- **macOS.** Скачайте установщик с того же [python.org/downloads](https://www.python.org/downloads/) или, если стоит Homebrew, выполните `brew install python`.
- **Linux.** Обычно Python уже есть.

### 2. Откройте командную строку

- **Windows:** меню "Пуск" → наберите "PowerShell" или "Терминал".
- **macOS:** Cmd + Пробел → наберите "Терминал".

Проверьте, что Python установился:

```bash
python3 --version     # macOS и Linux
py --version          # Windows
```

Должно появиться что-то вроде `Python 3.12.4`. Дальше в командах для Windows пишите `py` вместо `python3`.

### 3. Скачайте справочник

На странице репозитория нажмите зеленую кнопку **Code → Download ZIP** и распакуйте архив. Затем перейдите в папку в командной строке:

```bash
cd путь/к/папке/stepik-api-cookbook-main
```

Путь можно не набирать: напишите `cd ` с пробелом и перетащите папку в окно командной строки.

### 4. Установите библиотеку requests

```bash
python3 -m pip install requests     # macOS и Linux
py -m pip install requests          # Windows
```

### 5. Получите ключи и передайте их скриптам

Как создать ключи – в разделе [Приложение OAuth на Stepik](#приложение-oauth-на-stepik). Задайте их в том же окне командной строки:

```bash
# macOS и Linux
export STEPIK_CLIENT_ID="ваш Client id"
export STEPIK_CLIENT_SECRET="ваш Client secret"
```

```powershell
# Windows, PowerShell
$env:STEPIK_CLIENT_ID="ваш Client id"
$env:STEPIK_CLIENT_SECRET="ваш Client secret"
```

Ключи действуют, пока открыто это окно. В новом окне их нужно задать заново.

### 6. Запустите скрипт

Номер курса виден в адресе: в `stepik.org/course/12345/syllabus` это `12345`. Номер урока – в адресе `stepik.org/lesson/123456/step/1`, это `123456`.

```bash
python3 examples/backup_course.py 12345          # резервная копия курса в course-12345-backup.json
python3 examples/list_lesson_steps.py 123456     # шаги урока с номерами
python3 examples/find_in_steps.py 12345 "слово"  # где в курсе встречается слово
```

Чтобы посмотреть скрипты или поправить их под себя, удобно открыть папку в бесплатном редакторе [VS Code](https://code.visualstudio.com/): в нем есть встроенная командная строка (меню Terminal → New Terminal), и все команды выше работают там же.

### Если не сработало

| Что видно | Что сделать |
|---|---|
| `python3: command not found`, `Имя "python" не распознано` или `"python" не является внутренней или внешней командой` | Python не установлен или не добавлен в PATH. На Windows пишите `py`; если и он не находится, переустановите Python с галочкой "Add python.exe to PATH" и откройте новое окно командной строки |
| `No module named 'requests'` | Выполните шаг 4. Если библиотек несколько версий Python, ставьте той же командой, которой запускаете: `python3 -m pip …` или `py -m pip …` |
| `"pip" не является внутренней или внешней командой` | Пишите `py -m pip install requests` вместо `pip install requests` |
| `Задайте STEPIK_CLIENT_ID и STEPIK_CLIENT_SECRET в окружении` | Ключи не заданы в этом окне: выполните шаг 5 еще раз в том же окне, где запускаете скрипт |
| `Токен не получен: 401` | Ключ скопирован с лишним пробелом или у приложения не тот тип: нужен Confidential и Client credentials |
| `403: You do not have permission to perform this action` | Курс или шаг не ваш, или передан не тот номер: например, номер урока вместо номера шага |
| `403 от защиты Stepik, а не от API` | Слишком много запросов подряд. Подождите 10 минут и не запускайте скрипт повторно до этого |
| `CERTIFICATE_VERIFY_FAILED` на macOS | Python с python.org не установил сертификаты. Откройте папку "Программы → Python 3.x" и запустите `Install Certificates.command` |
| `cd: no such file or directory` | Неверный путь к папке. Перетащите папку в окно командной строки после `cd ` |

## Приложение OAuth на Stepik

1. Войдите на Stepik и откройте https://stepik.org/oauth2/applications/ – кнопка "Add application" (или сразу https://stepik.org/oauth2/applications/register/).
2. Client type – **Confidential**, Authorization grant type – **Client credentials**.
3. Сохраните и скопируйте Client id и Client secret.
4. Задайте их в командной строке, как в [шаге 5](#5-получите-ключи-и-передайте-их-скриптам) выше.

Пара Client id + Client secret дает полный доступ к вашему аккаунту без срока действия. Не коммитьте ее и не передавайте посторонним сервисам. Вход от имени других пользователей (authorization code) – в [docs/01-auth.md](docs/01-auth.md).

## Быстрый старт для тех, кто пишет код

### curl

```bash
# 1. Токен (живет около 10 часов)
TOKEN=$(curl -s -X POST https://stepik.org/oauth2/token/ \
  -u "$STEPIK_CLIENT_ID:$STEPIK_CLIENT_SECRET" \
  -d grant_type=client_credentials \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["access_token"])')

# 2. Кто я: id пользователя, которому принадлежит приложение
curl -s -H "Authorization: Bearer $TOKEN" https://stepik.org/api/stepics/1 \
  | python3 -c 'import sys, json; print(json.load(sys.stdin)["stepics"][0]["user"])'

# 3. Мои курсы (USER_ID – число из шага 2; страницы листаются через page=2, 3…)
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://stepik.org/api/courses?teacher=USER_ID&page=1"

# 4. Шаги урока: их id лежат в lessons[0].steps
curl -s -H "Authorization: Bearer $TOKEN" https://stepik.org/api/lessons/LESSON_ID
curl -s -g -H "Authorization: Bearer $TOKEN" \
  "https://stepik.org/api/step-sources?ids[]=STEP_ID_1&ids[]=STEP_ID_2"

# 5. Новый текст текстового шага
curl -s -X PUT -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  https://stepik.org/api/step-sources/STEP_ID \
  -d '{"stepSource": {"block": {"name": "text", "text": "<p>Новый текст</p>"}, "lesson": LESSON_ID, "position": 1}}'
```

Ключ `-g` нужен, чтобы curl не разбирал `[]` в адресе. В шаге 5 `lesson` и `position` берутся из ответа шага 4; у шага с заданием в `block` обязателен еще и полный `source` – см. [docs/05-step-types.md](docs/05-step-types.md).

### Python (`requests`)

```python
import os
import requests

API = "https://stepik.org/api"
LESSON_ID = 123456  # id своего урока

r = requests.post(
    "https://stepik.org/oauth2/token/",
    data={"grant_type": "client_credentials"},
    auth=(os.environ["STEPIK_CLIENT_ID"], os.environ["STEPIK_CLIENT_SECRET"]),
    timeout=20,
)
r.raise_for_status()
s = requests.Session()
s.headers["Authorization"] = "Bearer " + r.json()["access_token"]

# кто я
me = s.get(f"{API}/stepics/1", timeout=30).json()["stepics"][0]["user"]

# мои курсы, все страницы
courses, page = [], 1
while True:
    d = s.get(f"{API}/courses", params={"teacher": me, "page": page}, timeout=30).json()
    courses += d["courses"]
    if not d["meta"]["has_next"]:
        break
    page += 1
for c in courses:
    print(c["id"], c["title"])

# шаги урока (не больше 30 id за запрос)
lesson = s.get(f"{API}/lessons/{LESSON_ID}", timeout=30).json()["lessons"][0]
steps = s.get(f"{API}/step-sources", params={"ids[]": lesson["steps"][:30]}, timeout=30).json()["step-sources"]
for st in sorted(steps, key=lambda x: x["position"]):
    print(st["position"], st["id"], st["block"]["name"])

# дописать абзац в первый текстовый шаг
st = next(x for x in steps if x["block"]["name"] == "text")
st["block"]["text"] += "<p>Добавлено скриптом.</p>"
payload = {"stepSource": {"block": st["block"], "lesson": st["lesson"], "position": st["position"]}}
s.put(f"{API}/step-sources/{st['id']}", json=payload, timeout=30).raise_for_status()
```

Аккуратная версия того же самого, с паузами, повторами и пробным прогоном, – в [examples/](examples/).

## Оглавление

| Файл | О чем |
|---|---|
| [01-auth.md](docs/01-auth.md) | client_credentials, authorization code, refresh-токены, "кто я" |
| [02-structure.md](docs/02-structure.md) | курс → модуль → unit → урок → шаг, id и позиции |
| [03-reading.md](docs/03-reading.md) | формат ответов, пагинация, `ids[]`, фильтры, которые врут |
| [04-writing.md](docs/04-writing.md) | `PUT` полным объектом, создание курса и урока, позиции, готовность шагов |
| [05-step-types.md](docs/05-step-types.md) | `block` и `source` каждого типа шага, санитайзер HTML, пределы длины полей |
| [06-media.md](docs/06-media.md) | загрузка видео, видео-превью курса, картинки и доступность CDN |
| [07-comments-and-announcements.md](docs/07-comments-and-announcements.md) | комментарии, уведомления, новости курса и триггеры |
| [08-errors-and-limits.md](docs/08-errors-and-limits.md) | тело ошибок, повторы на 429/5xx, как не попасть под блокировку |
| [09-permissions.md](docs/09-permissions.md) | команда курса, приглашения, баны, рецензирование |

## Примеры

Python 3.8+, только стандартная библиотека и `requests` (`pip install requests`). Каждый скрипт берет `STEPIK_CLIENT_ID` и `STEPIK_CLIENT_SECRET` из окружения, делает паузу между запросами и останавливается, если Stepik ответил блокировкой.

| Скрипт | Что делает | Пишет в Stepik |
|---|---|---|
| [backup_course.py](examples/backup_course.py) | выгружает курс целиком (модули, уроки, шаги с ответами) в один JSON | нет |
| [list_lesson_steps.py](examples/list_lesson_steps.py) | печатает шаги урока: тип, начало текста, статус сборки | нет |
| [find_in_steps.py](examples/find_in_steps.py) | ищет строку или регулярное выражение во всех шагах курса | нет |
| [update_text_step.py](examples/update_text_step.py) | заменяет текст одного текстового шага; без `--apply` только показывает | да, с `--apply` |

## Лицензия

Тексты (этот README и `docs/`) – [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Код (`examples/` и фрагменты кода в текстах) – MIT. Полные тексты обеих лицензий – в [LICENSE](LICENSE).

---

Профиль автора на Stepik – [stepik.org/users/483341705](https://stepik.org/users/483341705/teach).
