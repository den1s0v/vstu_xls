Для запуска массовой обработки xls(x)-файлов расписания занятий (не экзаменов) ВолгГТУ нужно:

1. Подготовка

- скачать xls(x)-файлы расписания занятий [с оф. сайта](https://www.vstu.ru/student/raspisaniya/zanyatiy/index.php)
- сложить все скачанные xls(x)-файлы в одну папку (подпапки произвольной глубины допускаются)

1. Парсинг документов
  - запустить `python demo/batch_demo.py --input-dir "<полный путь к папке>"`
  - или
  - настроить в batch_demo.py входную директорию около строки 20 -- переменная `default_input_dir`
  - запустить `python demo/batch_demo.py`

  - по умолчанию результат (с сохранением структуры папок) будет помещён в:
    - `data/output` -- JSON-файлы документов
    - `data/reports` -- отчёты

2. Извлечение метаданных
  - запустить `python src/vstuxls/cli/build_schedule_metadata.py`
  - это соберёт `data/schedule_metadata.json` из всех файлов в `data/output`.
