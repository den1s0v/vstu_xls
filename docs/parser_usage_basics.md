# Базовое использование парсера

## Грамматика

Главный файл грамматики по умолчанию: `cnf/grammar_root.yml` (с подключением дополнительных YAML через `include_grammars`).

Смысл полей паттернов (`kind`, `inner`, `location`, `count_in_document` и т.д.) раскрывается в комментариях внутри YAML и в коде загрузки грамматики — здесь отметим только, что **изменение грамматики** — основной способ подстроить разбор под новый вид входного документа (таблицы).

## Запуск из демо-скриптов

Из корня репозитория (при установленном пакете `vstuxls` в `PYTHONPATH` или в режиме разработки):

- **Один файл + тяжёлый debug по волнам** — `demo/debug_demo.py`  
  В каталог `--output` записывается JSON-файл результатами разбора + снимки волн (JSON/Excel по флагам) и при обычном режиме также **`parsing_diagnostics.json`**.

- **Пакетная обработка каталога** — `demo/batch_demo.py`  
  Для каждого `.xlsx` создаётся:
  - подпапка в output с JSON-файлом (имя как у исходного файла) с результами парсинга;
  - подпапка в `--report-base` с отчётами; по умолчанию туда же пишется **`parsing_diagnostics.json`**.

### Полезные флаги

- Флаги волн (`--no-json` / `--no-excel` в демо) управляют только "тяжёлым" экспортом волн.
- `--no-diagnostics` — не записывать `parsing_diagnostics.json` (остальной разбор без изменений).

## Программный вызов

Рекомендуемая точка входа высокого уровня — `DocumentParsingService`:

1. Создать сервис с грамматикой.
2. При необходимости задать `diagnostics_output_dir`, `document_source_path`, `grammar_source_path` — тогда после `parse_document` появится JSON-диагностика.
3. Вызвать `parse_document(grid)` и при необходимости — `export_final_report` для отчётов вроде `unused_patterns.json`.

Минимальный пример-набросок для запуска:

```python
from pathlib import Path
from vstuxls.grammar2d import read_grammar
from vstuxls.services import DocumentParsingService

# подготовка грамматики и парсера для неё
grammar = read_grammar(Path("cnf/grammar_root.yml"))
service = DocumentParsingService(
    grammar=grammar,
    diagnostics_output_dir=Path("data/reports/my_doc"), # куда класть отчёты, а также
    document_source_path="источник.xlsx",               # передаём пути для экспорта
    grammar_source_path="cnf/grammar_root.yml",         # в нужные папки
)
# загрузка документа и обработка его парсером
grid = ...  # ExcelGrid или другой Grid
matches = service.parse_document(grid)
```
