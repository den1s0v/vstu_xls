# vstu_xls
Parsing human-made Excel (.xls) sheets into machine-readable form.  
Main application of the configurable project is to deal with [VSTU's timetable files](https://www.vstu.ru/student/raspisaniya/zanyatiy/) (in Russian).

# Status / Статус
Only an idea, first experiments. / Формируется идея, первые пробы инструментов.

### Частичная структура проекта (наброски)
![Структура проекта](https://github.com/den1s0v/vstu_xls/blob/main/materials/О%20парсинге%20xls.png?raw=true)

### Средства

* [xlrd](https://pypi.org/project/xlrd/) для извлечения информации о содержимом и форматировании ячеек, а также о границах между ними
* re (регулярные выражения) для классификации и получения содержимого ячеек 
* (?) [sly](https://sly.readthedocs.io)  для разбора DSL, описывающего структурные шаблоны/паттерны расположения простых ячеек в составе комплексных

  
