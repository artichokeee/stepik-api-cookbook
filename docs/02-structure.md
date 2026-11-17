# 02. Структура курса

```
course (курс)
└── section (модуль)
    └── unit (привязка урока к модулю)
        └── lesson (урок)
            └── step (шаг)
```

Урок – самостоятельный объект. В модуль его ставит `unit`: запись "этот урок стоит в этом модуле на этой позиции". Позиции считаются с 1.

## Где лежат id

| Объект | Ресурс | Ключевые поля |
|---|---|---|
| курс | `/api/courses` | `id`, `title`, `sections` – id модулей |
| модуль | `/api/sections` | `id`, `title`, `course`, `position`, `units` – id привязок |
| привязка | `/api/units` | `id`, `section`, `lesson`, `position` |
| урок | `/api/lessons` | `id`, `title`, `is_public`, `steps` – id шагов, `units`, `courses`, `is_orphaned`, `cover_url` |
| шаг (чтение) | `/api/steps` | `id`, `lesson`, `position`, `status`, `reason_of_failure`, `instruction` |
| шаг (автор) | `/api/step-sources` | `id`, `lesson`, `position`, `block`, `cost`, `max_submissions_count` |

`course.sections` в ответе уже отсортирован по `position`. У одного шага один id: число из `lesson.steps` подходит и для `/api/steps`, и для `/api/step-sources`.

## Два ресурса для шагов

**Ожидание:** шаги правятся через `/api/steps`.
**На деле:** `/api/steps` только читает. Создание, правка и удаление шага – через `/api/step-sources`. Там же лежит `block` целиком, вместе с правильными ответами, поэтому читать его может только преподаватель курса.
**Что делать:** содержимое шага – `step-sources`; состояние сборки (`status`, `reason_of_failure`) и признак рецензирования (`instruction`) – `steps`.

## Обход курса

```python
course = get("/courses/{id}")["courses"][0]
sections = by_ids("sections", course["sections"])           # не sections?course=
units    = by_ids("units", [u for s in sections for u in s["units"]])
lessons  = by_ids("lessons", [u["lesson"] for u in units])
steps    = by_ids("step-sources", [x for l in lessons for x in l["steps"]])
```

`by_ids` – чтение по `ids[]` пачками по 30 ([03-reading.md](03-reading.md)). Целиком, с паузами и повторами, это сделано в [examples/backup_course.py](../examples/backup_course.py).

**Ожидание:** модули курса отдаст `GET /api/sections?course=<id>`.
**На деле:** этот фильтр возвращает пустой список.
**Что делать:** берите id модулей из `course.sections` и читайте их по `ids[]`.

## Где стоит урок

От урока к курсу – через привязку: `GET /api/units?lesson=<lessonId>` → `units[0].section` → `GET /api/sections/<id>` → `course`. Этот фильтр работает.

Урок без единой привязки Stepik помечает `is_orphaned: true`, а `units` и `courses` у него пустые. Такой урок существует со всеми шагами, но ни в одной программе его нет.

Перед созданием привязки проверьте `units?lesson=<id>`: вторая привязка того же урока даст в программе два одинаковых урока.

## Позиции

Позиция – просто число в объекте. Stepik не следит за уникальностью и не сдвигает соседей, подробности – в [04-writing.md](04-writing.md#позиции-соседи-не-сдвигаются).

## Команда курса

Роли в курсе – это группы, id которых лежат в полях курса: `admins_group`, `teachers_group`, `assistants_group`, `moderators_group`, `testers_group`, `learners_group`. Подробнее – [09-permissions.md](09-permissions.md).
