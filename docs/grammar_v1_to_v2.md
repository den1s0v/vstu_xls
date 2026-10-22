# Миграция грамматики с v1 на v2

Документ собирает всё, что нужно, чтобы перевести YAML-грамматику с диалекта v1
(как в `cnf/grammar_root.yml`) на диалект v2 (`grammar: 2`).

Смежные материалы:

* [Формальная семантика](grammar_semantics.md) — *что означает* грамматика
* [Компилятор](grammar_compiler.md) — линтер, STN, движок, CLI
* Пример v2: `tests/test_data/v2_demo_grammar.yml`

---

## 1. Зачем мигрировать

В v1 автор грамматики вынужден знать **порядок проверок матчера** и часто
пишет «хаки»:

* `size` у компонента на самом деле ограничивает родителя;
* `weight: -10` вместо «здесь не должно быть X»;
* `kind: general` + куча `extends` вместо явной альтернативы;
* `allows_overlapping: true`, чтобы жадная фильтрация не съела нужные совпадения;
* lookahead в регулярках вместо приоритетов типов ячеек.

Диалект **v2** отделяет:

1. **структуру** — множество допустимых разборов (геометрия + типы ячеек);
2. **политику** — что выбрать среди разборов (`priority`, `prefer`, `overlap`, `confidence`).

Порядок поиска выводит планировщик из STN; «опорные линии» в голове автора больше не нужны.

**Корпус v1 не обязан переписываться.** Старые файлы читаются как раньше;
компилятор только диагностирует странности (`G020`, `POL004`, …). Миграция —
по желанию, для новых паттернов или рефакторинга.

---

## 2. Как включить v2

В **корне любого** файла грамматики (или импортируемого фрагмента):

```yaml
grammar: 2
```

Достаточно встретить `grammar: 2` хотя бы в одном загруженном файле —
фронтенд переключает весь IR в диалект 2 (`GrammarIR.dialect = 2`).

Проверка после правок:

```text
vstuxls-grammar check path/to/grammar.yml
vstuxls-grammar explain path/to/grammar.yml PATTERN
vstuxls-grammar fuzz path/to/grammar.yml --count 20
```

Из исходников (Windows `cmd`): `set PYTHONPATH=src && uv run python -m vstuxls.grammar2d.compiler …`.

---

## 3. Смена модели смысла (кратко)

| Раньше (на практике v1) | В v2 |
|-------------------------|------|
| Порядок проверок и «опорные линии» зашиты в голову автора | Геометрия → два STN (оси x/y); порядок join выводит планировщик |
| Противоречия: «матчер ничего не нашёл» | `check` / `explain`: GEO001 со свидетелем-циклом |
| `weight: -10` ≈ «не должно быть» | секция `forbid` |
| `general` + `extends` = и иерархия, и альтернатива | чистое `kind: alt` + `one_of` |
| Политика смешана со структурой | структура vs `policies:` / `priority` / `prefer` / `overlap` |
| Lookahead в регулярках | `priority` / `except` у типа ячейки |

Семантика грамматики — *множество всех согласованных разборов*. Выбор подмножества
(«лучшие», без накладок) — слой политики, не геометрия.

---

## 4. Чеклист миграции: синтаксис и семантика

### 4.1. `size` у компонента — главная ловушка

| | v1 | v2 |
|---|----|----|
| `size` у **компонента** | ограничивал **родителя** (как старый матчер) | размер **самого** компонента |
| `size` у **терминала** (`kind: cell`) | матчер **не проверял** | проверяется |
| optional `inner` | не расширяет рамку родителя | **расширяет** рамку родителя |

**Миграция v1 → v2**

```yaml
# v1 (исторический смысл: высота родителя = 3)
lesson:
  kind: area
  inner:
    discipline:
      pattern: discipline_with_groups
      size: '2+ x 3'      # ← на самом деле size родителя!

# v2
lesson:
  kind: area
  size: '2+ x 3'          # размер области — у паттерна
  inner:
    discipline:
      pattern: discipline_with_groups
      # size компонента — только если нужно ограничить сам discipline
```

На v1 компилятор сам переносит component-`size` в паттерн и пишет **G020**.
После `grammar: 2` перенос **не** делается — проверьте, что размеры стоят там,
где вы их имеете в виду.

### 4.2. Альтернативы: `general`/`extends` → `alt`

```yaml
# v1
lesson:
  kind: general
# ... и много паттернов с extends: lesson

# v2
lesson:
  kind: alt
  one_of: [frame_based_lesson, frame_based_lesson_without_teacher]
```

`extends` остаётся для «является разновидностью» (совпадение ребёнка — совпадение базы).
Для чистого выбора без собственной геометрии используйте `alt`.

### 4.3. Отрицательные веса → `forbid` / `require`

```yaml
# v1
inner:
  _other_discipline:
    pattern: discipline_with_groups
    optional: true
    weight: -10.0
    location: { top: 2+ }

# v2
forbid:
  _other_discipline:
    pattern: discipline_with_groups
    location: { top: 2+ }
```

Аналогично «обязательный контекст без вклада в рамку» — секция `require`.

Диагностика на v1: **POL004** («отрицательный вес вместо forbid»).

### 4.4. Отношения между компонентами → `relations`

Вместо неявной «опорной линии» и хитрого порядка `location`:

```yaml
# v2
relations:
  - caption.top == value.top
  - caption.bottom == value.bottom
  - value.left == caption.right
  - title.bottom <= body.top
  - a.left - b.left in 0..2
```

Допустимые формы:

* `A.edge ==/<=/>=/</> B.edge [±k]`
* `A.edge - B.edge in a..b`

Имена `this` / `self` / `parent` / `element` — сама рамка паттерна.
Рёбра: `left`, `right`, `top`, `bottom`.

### 4.5. Повторяющиеся компоненты → `count`

```yaml
# v2
inner:
  remark:
    pattern: note
    count: 0..2    # → remark + remark_2 (второй optional), порядок сохраняется
```

Для неограниченного числа однотипных элементов по-прежнему `kind: array`.
Слишком большой или без верхней границы `count` — **G006** (подсказка: используйте array).

### 4.6. Выравнивание в массивах → `align`

```yaml
# v1: всегда неявное both (совпадение обеих поперечных сторон)
# v2:
fields:
  kind: array
  item_pattern: field
  direction: column
  gap: 0
  align: start    # both | start | end | none
```

### 4.7. Копипаста → `templates`

```yaml
templates:
  field:
    name: 'field_${kind}'
    params:
      kind: [text, number]
    exclude:                 # необязательно
      - { kind: number }     # пример: не порождать комбинацию
    when: 'kind != "skip"'   # необязательный фильтр (safe_eval)
    body:
      kind: area
      description: поле «подпись — ${kind}»
      inner:
        caption: { pattern: caption }
        value: { pattern: '${kind}_value' }
      relations:
        - caption.top == value.top
        - value.left == caption.right
```

В `${…}` — безопасная арифметика (`hours * 3 // 2`, `min`, `max`, …).
Одиночный паттерн из шаблона: `{ template: field, args: { kind: text } }`.

Ошибки шаблона — **G016**.

### 4.8. Политика отдельно от структуры

```yaml
# можно оставить поля в паттерне (как в v1):
field_number:
  kind: area
  confidence: 0.95
  priority: 1
  prefer: [field_text]
  overlap:
    mode: partial
    resolution: ['height-min', 'width-max', 'precision-max']

# или вынести:
policies:
  field_number:
    confidence: 0.95
    priority: 1
    prefer: [field_text]
    exclusive: true          # бывший allows_overlapping: false
```

Соответствия:

| v1 | v2 / политика |
|----|----------------|
| `allows_overlapping: true` | `exclusive: false` (или оставить флаг — фронтенд понимает оба) |
| `allows_overlapping: false` | `exclusive: true` (по умолчанию) |
| жадная фильтрация, чтобы «не съело» | не нужна: движок собирает разборы, политика выбирает |
| ручной lookahead в regex | у типа ячейки: `priority`, `except: [other_type]` |

Неоднозначные альтернативы без правила выбора — **AMB001**;
с правилом — **AMB002** (info).

### 4.9. Импорт файлов

```yaml
# v1
include_grammars: [lesson_frames.yml]

# v2 (оба работают)
import: [common_cell_types.yml]
include_grammars: [lesson_frames.yml]
```

Повторный импорт / цикл — **G018** (файл пропускается).

### 4.10. Что в записи почти не меняется

* `kind: cell | area | array | array-in-context`
* `inner` / `outer` + `location` (`top`, `left: 0..1`, `margin-top: 0+`, …)
* `content_type`, `cell_types` / `cell_types_filepath`
* `item_pattern`, `direction`, `item_count`, `gap`, `allow_breakdown`
* `root`, `count_in_document`, `description`, `style`

---

## 5. Рекомендуемый порядок работ

1. **Не меняя диалект**, прогнать `check` на текущей грамматике.
   Зафиксировать G020 / POL004 / AMB001 / LEX001 — это карта будущих правок.
2. Для одного поддерева (или нового файла) поставить `grammar: 2`.
3. Перенести component-`size` на паттерны (см. 4.1); убедиться, что `check` без GEO001.
4. Заменить `weight: -N` на `forbid`; явные альтернативы — на `alt`.
5. Где «приклеить A к B» читалось только из порядка матчинга — добавить `relations`.
6. Вынести `confidence` / `priority` / `prefer` / `overlap` в `policies:`.
7. Убрать копипасту через `templates`.
8. `explain PATTERN` — сверить вычисленные размеры и окна.
9. `fuzz --pattern PATTERN` — самопроверка (на сложных паттернах вроде
   `weeks_calendar` генератор может честно сказать «не удалось породить»).
10. `diff grammar.yml table.xlsx` — сравнить корни со старым матчером
    (на переходном этапе; полное совпадение всех промежуточных паттернов
    не требуется — новый движок полнее).

---

## 6. Диагностики, которые ведут миграцию

| Код | Смысл | Что сделать при переходе на v2 |
|-----|--------|--------------------------------|
| **G020** | v1: `size` компонента = размер родителя | перенести `size` на паттерн |
| **POL004** | отрицательный вес вместо forbid | секция `forbid` |
| **POL001** | `allows_overlapping` откладывает конфликт | явный `overlap` / `alt` / array; убрать флаг, если он был костылём |
| **AMB001** | альтернативы могут совпасть без правила | `priority` / `prefer` / `overlap` |
| **LEX001** | типы ячеек делят строки | `priority` / `except` у типа или оставить, если различает структура |
| **GEO001** | противоречивые location/size/relations | ослабить диапазон или сделать компонент optional |
| **G002 / G003 / G012** | битые ссылки, циклы | починить до смены диалекта |
| **G016** | ошибка шаблона | проверить `name`/`body`/`params` и `${…}` |

Полный список кодов — `src/vstuxls/grammar2d/compiler/diagnostics.py::CODES`.

---

## 7. Осознанные отличия движка (не синтаксис, но влияют на «ожидаемое»)

После миграции и при сравнении со старым матчером (`diff`):

1. Новый движок **полнее**: не отбрасывает кандидатов эвристикой «пересекающихся
   совпадений своего паттерна» → больше альтернатив; выбор — политикой.
2. Рамка родителя может быть шире охвата `inner`, если её однозначно задаёт контекст
   (`padding-top: 0` к outer + фиксированный `size`).
3. В v2 `size` терминала проверяется; в v1 по умолчанию — нет (`strict_cell_size=False`).
4. Массивы `fill` / `allow_breakdown` считаются иначе → число под-массивов может
   отличаться; **корни** на рабочих корпусах совпадают.
5. На один `count_in_document` остаётся лучший разбор одной рамки.

Это не баги миграции YAML, а смена семантики выполнения. Подробнее —
[grammar_compiler.md](grammar_compiler.md), раздел «Осознанные отличия».

---

## 8. Минимальный пример «до / после»

**v1 (идея):** два почти одинаковых поля, отрицательный вес, size у компонента.

```yaml
patterns:
  field_text:
    kind: area
    allows_overlapping: true
    inner:
      caption: { pattern: caption }
      value: { pattern: text_value, size: '1+ x 1' }  # на деле size родителя
      _left:
        pattern: caption
        optional: true
        weight: -10
        location: { margin-left: 0 }
```

**v2:**

```yaml
grammar: 2

templates:
  field:
    name: 'field_${kind}'
    params: { kind: [text, number] }
    body:
      kind: area
      size: 1+ x 1
      inner:
        caption: { pattern: caption }
        value: { pattern: '${kind}_value' }
      relations:
        - caption.top == value.top
        - value.left == caption.right
      forbid:
        glued_caption:
          pattern: caption
          location: { margin-left: 0 }

patterns:
  field:
    kind: alt
    one_of: [field_text, field_number]

policies:
  field_number:
    confidence: 0.95
```

Полный рабочий файл: `tests/test_data/v2_demo_grammar.yml`.

---

## 9. Что можно не мигрировать сразу

* Весь `cnf/grammar_root.yml` и связанные include — можно оставить на v1;
  компилятор и новый движок их понимают.
* Постепенный перенос: новый файл с `grammar: 2` + `import` старых фрагментов
  (учтите: флаг диалекта глобальный для сессии загрузки — при смешении
  файлов с `grammar: 2` и без него доминирует v2-семантика `size`).
* Регулярки `cell_types` — достаточно добавить `priority`/`except` там,
  где `LEX001` реально мешает, а не переписывать все паттерны.

---

## 10. Краткая шпаргалка

```text
grammar: 2                          # включить диалект
size у паттерна, не у компонента    # было наоборот в v1
forbid / require                    # вместо weight: -N
kind: alt + one_of                  # вместо general+extends для выбора
relations: [...]                    # вместо опорных линий
count: a..b                         # квантор компонента
align: start|end|both|none          # массивы
templates: + ${expr}                # анти-копипаста
policies:                           # выбор разбора отдельно
priority / except у cell_type       # вместо lookahead
check → explain → fuzz → diff       # конвейер уверенности
```
