# Формат отчёта `parsing_diagnostics.json`

Файл создаётся в UTF-8, валидный JSON с отступами (как в проекте принято для отчётов).

## Корень

| Поле | Тип | Описание |
|------|-----|----------|
| `document` | object | Метаданные прогона |
| `summary` | object | Агрегированные счётчики |
| `issues` | array | Список проблем и событий |

## `document`

| Поле | Тип | Описание |
|------|-----|----------|
| `source_path` | string \| null | Путь к исходному документу, если передан в сервис |
| `grammar_path` | string \| null | Путь к YAML грамматики, если передан |
| `started_at` | string | Время начала (UTC, ISO 8601) |
| `finished_at` | string | Время окончания (UTC, ISO 8601) |
| `duration_ms` | number | Длительность в миллисекундах |

## `summary`

| Поле | Тип | Описание |
|------|-----|----------|
| `errors_count` | int | Число записей с `severity: "error"` |
| `warnings_count` | int | Число записей с `severity: "warning"` |
| `infos_count` | int | Число записей с `severity: "info"` |
| `root_matches_count` | int | Сколько корневых совпадений вернул разбор |

## Элемент `issues[]`

Обязательные поля:

- `severity` — `"error"` \| `"warning"` \| `"info"`
- `code` — стабильный идентификатор для скриптов
- `message` — краткое описание на русском или нейтральном языке

Опциональный контекст (появляется по мере необходимости):

- `pattern_name`, `wave_index`, `expected`, `actual`, `box`, `source`, `exception_type`, `detail`

### Коды (MVP)

| Код | Уровень | Когда |
|-----|---------|--------|
| `PATTERN_COUNT_MISMATCH` | warning | Число найденных совпадений паттерна не попало в ожидаемый диапазон `count_in_document` |
| `MATCH_LIMIT_APPLIED` | warning | Список совпадений усечён до лимита (например, `count_in_document.stop`) |
| `OVERLAP_RESOLUTION_UNEXPECTED_MODE` | warning | Неизвестный режим разрешения перекрытий; фильтрация не применена |
| `PARSE_EXCEPTION` | error | Исключение во время `parse_document`; в `detail` — фрагмент трассировки |

Новые коды могут добавляться без изменения общей схемы файла.
