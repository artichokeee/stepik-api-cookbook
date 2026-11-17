# 05. Типы шагов

Шаг – это `block`: `name` (тип), `text` (HTML условия или текста) и для заданий `source` (настройки и ответы). Официальной схемы `source` нет; формы ниже сняты с живого API: шаг каждого типа создавался в тестовом курсе и читался обратно.

**Ожидание:** необязательные ключи `source` можно опустить.
**На деле:** отсутствие "необязательного" ключа часто дает 400.
**Что делать:** отправляйте полный набор полей, как ниже. Если Stepik отклонил тело, прочитайте его жалобу – валидатор называет ключ сам (см. в конце).

## Текст и развернутый ответ

- **text** – `{"name": "text", "text": "<p>HTML</p>"}`, без `source`.
- **free-answer** – `source: {is_attachments_enabled: false, is_html_enabled: true, manual_scoring: false}`.

## Задания с закрытым ответом

- **choice** – `source: {options: [{is_correct, text, feedback}], is_multiple_choice, sample_size, preserve_order, is_html_enabled: true, is_always_correct: false, is_options_feedback: false}`. `sample_size` не больше числа вариантов.
- **string** – `source: {pattern, case_sensitive, match_substring, use_re, code: "", is_text_disabled: false, is_file_disabled: true}`.
- **number** – `source: {options: [{answer: "4.0", max_error: "0.01"}], sample_size: 1}`. Числа – строками.
- **matching** – `source: {pairs: [{first, second}], preserve_firsts_order: true, is_html_enabled: true}`. Значения `second` должны быть уникальны во всех парах, иначе 400 "Ambiguous pairs".
- **sorting** – `source: {options: [{text}], is_html_enabled: true}`. Порядок массива и есть правильный порядок.
- **fill-blanks** – `source: {components: [...], is_case_sensitive: false}`. У **каждого** компонента должны быть и `text`, и `options`, иначе 400:
  - текст: `{type: "text", text: "…", options: []}`;
  - пропуск: `{type: "select", text: "", options: [{text, is_correct}]}`.
- **table** – `source: {description, rows: [{name, columns: [{choice: bool}]}], columns: [{name}], options: {is_checkbox, is_randomize_rows, is_randomize_columns, sample_size}, is_always_correct}`. Порядок `columns` в строке совпадает с массивом `columns`. Настройки лежат **внутри** `options` (на верхнем уровне их отвергают), а `is_always_correct` наоборот – снаружи.

### Свои комментарии к ответу

`feedback_correct` и `feedback_wrong` – поля самого `block`, а не `source`. Работают для любого автоматически проверяемого типа, не только для `choice`.

## Исполняемые типы

Собираются асинхронно после 201 – проверяйте `status` через `GET /api/steps/<id>` ([04-writing.md](04-writing.md#201-created-не-значит-что-шаг-работает)).

- **code** – `source: {code (проверка на Python), templates_data ("::python3\n<шаблон>"), test_cases: [["вход", "выход"]], test_archive: [], samples_count, execution_time_limit, execution_memory_limit, is_time_limit_scaled, is_memory_limit_scaled, is_run_user_code_allowed, manual_time_limits: [], manual_memory_limits: []}`. `test_archive` обязателен, пустой список подходит; без него 400.
- **sql** – `source: {solve_sql, check_code, init_sql}`. Первые два обязательны, `init_sql` – скрипт подготовки базы, необязателен. Полей `initial_sql`, `is_sql_free`, `is_multiple_queries` нет. Две галочки редактора лежат в `source` (проверено в августе 2026):
  - `is_run_user_code_allowed` ("Разрешить любые SQL запросы", по умолчанию `true`) – только панель "Запустить" для отладки у ученика; на проверку не влияет;
  - `is_multiple_statements_allowed` ("Разрешить несколько SQL запросов в решении", по умолчанию `false`) – без нее решение из нескольких команд через `;` отклоняется с "Only one query is allowed".
- **dataset** – `source: {code}`, один ключ с Python-кодом, где есть `generate()`, `solve(dataset)`, `check(reply, clue)`. `generate()` должна вернуть **один** набор данных **строкой**; список (даже `['1 2']`) молча дает `status: error`.
- **math** – `source: {answer, numerical_test: {z_re_min, z_re_max, z_im_min, z_im_max, max_error, integer_only}}`. Все строки, кроме `integer_only` (bool). `numerical_test` обязателен целиком, даже если численная проверка не нужна. Пустой `answer` – ошибка `plugins.math.errors.answer-empty`.
- **random-tasks** (числовая задача со случайными данными) – `source: {task ("У Васи \\x яблок…"), solve ("x + y"), max_error (строка), ranges: [{variable, num_from, num_to, num_step}]}`. В тексте переменная с обратной косой чертой (`\\x`), в `ranges` – без нее.
- **html** (задача на HTML/CSS) – `source: {html_template, css_template, checklist: [{name, selector, tests: []}]}`. Пункт списка требует `name` и `tests` (не `description` и не `checks`).
- **video** – `{"name": "video", "text": "", "video": <объект видео>}`, см. [06-media.md](06-media.md).

### Проверка SQL: аргументы названы обманчиво

**Ожидание:** `check_code` получает ответ ученика и эталон, достаточно сравнить `reply == clue`.
**На деле:** `reply` – **текст** запроса ученика (строка), `clue` – **результат** этого запроса: `{columns, rows, affected_rows}`. Эталон в проверку не передается, поэтому `reply == clue` не совпадает никогда (проверено в июле 2026).
**Что делать:** сравнивайте результат с ожидаемым напрямую:

```python
def check(reply, clue):
    return clue.get('rows') == [['Аня']]
```

Никогда не пишите `return True`: Stepik сам ответы не сравнивает, и засчитается любой запрос, в том числе неверный.

**Ожидание:** галочка "несколько SQL запросов" влияет только на то, что принимает редактор.
**На деле:** она меняет **форму** `clue`: это становится список таких словарей, по одному на команду, а результат последнего запроса – `clue[-1]['rows']`. Проверка, написанная под словарь, падает с `AttributeError: 'list' object has no attribute 'get'`, шаг молча получает `status: error`, и ни один ученик его не откроет.
**Что делать:** включили галочку – перепишите проверку под список.

## Санитайзер HTML

Stepik чистит HTML шага при записи. Что остается, а что пропадает, выяснено так: шаг с набором разметки записывался в тестовый курс и читался обратно (июль 2026, дополнено в сентябре 2026).

| Остается | Вырезается |
|---|---|
| в `style`: `width`, `height`, `float`, `text-align`, `margin` (только сокращенная запись), `padding`, `border`, `color`, `background-color`, `font-size`, `font-weight`, `font-style` | в `style`: `display`, `flex`, `gap`, `grid-*`, `border-radius`, `max-width`, `min-width`, `margin-left/right/top/bottom`, `clear`, `vertical-align`, `line-height`, `text-decoration`, `white-space`, `overflow`, `position`, `box-shadow`, `opacity`, `transform` |
| атрибуты `width`, `height`, `class`, `src`, `colspan` | атрибут `align` целиком |
| теги `table`, `thead`, `tbody`, `tr`, `th`, `td`, `figure`, `figcaption`, `div`, `pre`, `code` | встроенный `<svg>` и адреса `data:` – целиком |
| `<iframe src width height allowfullscreen>` | у `iframe` – только `frameborder` |

Следствия:

- Раскладку картинок можно собрать только из `float` и сокращенного `margin`, например `margin: 0 16px 12px 0`. Скругленные углы рисуйте в самой картинке.
- Центрирование, которое переживает санитайзер, – только `<p style="text-align:center">`.
- `<img>` – строчный элемент: две картинки подряд встанут рядом, даже если в редакторе они выглядят одна под другой. Каждую отдельную картинку оборачивайте в свой `<p>`.
- Схема или диаграмма – только загруженной картинкой по `<img src>`, не встроенным SVG ([06-media.md](06-media.md#svg)).
- `iframe` проходит, поэтому видео и слайды можно встраивать через API, а не только через редактор (июль 2026).

## Пределы длины полей

Официальной таблицы нет, но валидатор называет предел сам: `{"title": ["Убедитесь, что это значение содержит не более 64 символов (сейчас 89)."]}`. Один запрос с заведомо длинными значениями во всех полях снимает пределы всех полей сразу и ничего не портит – до записи он не доходит. Замер августа 2026:

| Объект | Поле | Предел |
|---|---|---|
| курс | `title`, `title_en`, `workload` | 64 |
| курс | `certificate` | 256 |
| курс | `summary` | 512 в редакторе Stepik (API принимает больше), для публикации не меньше 100 |
| модуль | `title` | 64 |
| урок | `title` | 64 |
| новость курса | `subject` | 255 |

У `description`, `requirements`, `target_audience`, `learning_format`, `acquired_skills`, `acquired_assets` предела нет: 5000 символов прошли.

**Ожидание:** если API принял значение, редактор Stepik тоже его примет.
**На деле:** редактор строже. `summary` API принимает и в 5000 символов, а редактор показывает счетчик `430/512` и больше сохранить не дает; для публикации курса нужно еще и не меньше 100 символов ("Для публикации нужно больше 100 символов").
**Что делать:** если в редакторе Stepik у поля есть счетчик, ориентируйтесь на него, а не на ответ API.

## Как читать жалобы валидатора

Валидатор называет проблему прямо, и по жалобам схему можно вывести перебором: отправить тело, прочитать жалобу, поправить, повторить. Делайте паузу между попытками и ограничьте их число ([08-errors-and-limits.md](08-errors-and-limits.md)).

| Жалоба | Значит |
|---|---|
| `required key not provided @ data['x']` | не хватает ключа `x` |
| `Expected key x in {...}` | нужен ключ `x` |
| `extra keys not allowed @ data['x']` | ключ `x` лишний (или стоит не на том уровне) |
| `Expected str, got 0` | значение должно быть строкой |
| `plugins.<тип>.errors.<код>` | ошибка проверки содержимого, например `plugins.math.errors.answer-empty`, `plugins.fill-blanks.errors.blanks-empty` |
