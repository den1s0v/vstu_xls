"""Набросок структуры программы и API для автоматического повторения ручных корректировок данных, преимущественно строковых.
    Полезно для тех алгоритмов, которые регулярно обрабатывают одни и те же / сильно похожие данные.

    АРХИТЕКТУРА:
    
    Двухслойная модель:
    - Слой входных данных: Occurrence (вхождения, необработанные данные)
    - Слой корректировок: CorrectObject (корректные объекты с ID из справочников)
    - Разрешение/привязка: Resolution (связь между слоями)
    
    Связи: Occurrence → Resolution (один-ко-многим), Resolution → CorrectObject (многие-к-одному)
    
    МЕХАНИЗМ РАЗРЕШЕНИЯ:
    
    CorrectObject хранит required_context_elements (обязательные элементы контекста). Resolution создается автоматически со статусом PENDING при совпадении элементов контекста:
    
    Проверка соответствия элемента контекста:
    - Элемент присутствует в Occurrence и значения совпадают → СООТВЕТСТВУЕТ
    - Элемент отсутствует в Occurrence:
      * absence_allowed=True → СООТВЕТСТВУЕТ (тип может быть неизвестен заранее), но score Resolution будет меньше
      * absence_allowed=False → НЕ СООТВЕТСТВУЕТ (тип должен быть известен заранее) - Resolution не создается
    - Элемент присутствует, но значения различаются:
      * important=True → НЕ СООТВЕТСТВУЕТ - Resolution не создается
      * important=False → СООТВЕТСТВУЕТ, но score Resolution будет меньше
    
    "Разрешение" может быть переопределено вручную для любой пары (в т.ч. создано без оглядки на контекст, или переназначено, или удалено).
    APPROVED может быть назначено для каждого Occurrence максимум 1 раз и имеет приоритет над остальными статусами.
    
    Вычисление score для Resolution (при неоднозначности):
    score = 10 * (оценка близости по value) + взвешенная сумма совпавших элементов контекста
    - Оценка близости по value: простое равенство (=1), затем Jaro-Winkler для неполного совпадения
    - Веса элементов контекста: используются weight из ContextElement
    - Нормализация score не требуется
    - При совпадении оценок выбирается первое по списку
    
    Явный INVALID не участвует в выборе корректного объекта.
    При отсутствии подходящего корректного объекта для Occurrence создается новый CorrectObject без изменения содержимого.
    
    КЕШИРОВАНИЕ resolved_to:
    - Источник эталона: набор всех CorrectObject в рамках текущего scope_id
    - Инвалидация: любое изменение любого CorrectObject с этим scope_id приводит к инвалидации кешей и пересчету всех Resolution с этим scope_id
    - Проверка актуальности: сравнение даты кеширования resolved_to с scope.updated_at (из таблицы scopes)
    - Если resolved_to.updated_at < scope.updated_at → требуется пересчет, иначе можно использовать кешированное значение
    
    УНИКАЛЬНОСТЬ:
    - Occurrence: по value и контексту. Новый не добавляется, если уже существует такой, набор элементов контекста которого полностью покрывает элементы контекста кандидата (все элементы кандидата присутствуют в существующем с теми же значениями). Признаки important и absence_allowed не учитываются при проверке покрытия для Occurrence.
    - CorrectObject: по external_id (если указан) или по value + required_context_elements.
    - Resolution: по паре (Occurrence, CorrectObject).


    СТРУКТУРА БАЗЫ ДАННЫХ:

    Четыре основные таблицы:

    0. Таблица `scopes` (области действия):
       - id (PRIMARY KEY, автоинкремент)
       - description (TEXT, NULLABLE) - описание области действия
       - updated_at (TIMESTAMP, NOT NULL) - дата последнего изменения любого CorrectObject в этом scope
       
       Индексы:
       - INDEX(updated_at) - для проверки актуальности кеша

    1. Таблица `occurrences` (входные объекты):
       - id (PRIMARY KEY, автоинкремент)
       - value (TEXT, NOT NULL) - текстовое значение вхождения
       - context (JSON/TEXT, NOT NULL) - массив элементов контекста [{"key": str, "value": str, "important": bool, "weight": float, "absence_allowed": bool}]
       - score (FLOAT, DEFAULT 1)
       - approved (BOOLEAN, DEFAULT FALSE)
       - manual (BOOLEAN, DEFAULT FALSE)
       - scope_id (INTEGER, FOREIGN KEY -> scopes.id, NOT NULL, DEFAULT 0)
       - updated_at (TIMESTAMP, NOT NULL) - дата последнего изменения / кеширования resolved_to
       - resolved_to_id (INTEGER, FOREIGN KEY -> correct_objects.id, NULLABLE) - кеш, ссылка на CorrectObject

       Индексы:
       - UNIQUE(value, context) - для проверки покрытия контекста
       - INDEX(value) - для быстрого поиска по значению
       - INDEX(scope_id) - для фильтрации по области действия
       - INDEX(resolved_to_id) - для быстрого доступа к кешированному результату

    2. Таблица `correct_objects` (корректные объекты):
       - id (PRIMARY KEY, автоинкремент)
       - external_id (TEXT, NULLABLE, UNIQUE) - ID из внешнего справочника
       - value (TEXT, NOT NULL) - текстовое значение корректного объекта
       - required_context_elements (JSON/TEXT, NOT NULL) - массив обязательных элементов контекста [{"key": str, "value": str, "important": bool, "weight": float, "absence_allowed": bool}]
       - context (JSON/TEXT, NOT NULL) - массив элементов контекста (для совместимости с Item)
       - score (FLOAT, DEFAULT 1)
       - approved (BOOLEAN, DEFAULT FALSE)
       - manual (BOOLEAN, DEFAULT FALSE)
       - scope_id (INTEGER, FOREIGN KEY -> scopes.id, NOT NULL, DEFAULT 0)
       - updated_at (TIMESTAMP, NOT NULL)
       - name (TEXT, NULLABLE) - название объекта из справочника
       - description (TEXT, NULLABLE) - описание объекта из справочника

       Индексы:
       - UNIQUE(external_id) WHERE external_id IS NOT NULL - уникальность по внешнему ID
       - UNIQUE(value, required_context_elements) WHERE external_id IS NULL - уникальность по value + required_context_elements
       - INDEX(value) - для быстрого поиска по значению
       - INDEX(scope_id) - для фильтрации по области действия
       - INDEX(external_id) - для поиска по внешнему ID
       
       Триггеры/События:
       - При изменении (INSERT/UPDATE/DELETE) любого CorrectObject обновлять scopes.updated_at для соответствующего scope_id

    3. Таблица `resolutions` (преобразования/разрешения):
       - id (PRIMARY KEY, автоинкремент)
       - occurrence_id (INTEGER, FOREIGN KEY -> occurrences.id, NOT NULL)
       - correct_object_id (INTEGER, FOREIGN KEY -> correct_objects.id, NOT NULL)
       - manual (BOOLEAN, DEFAULT FALSE) - создано/обновлено вручную или автоматически
       - status (INTEGER, DEFAULT 0, NOT NULL) - 0=PENDING, 1=APPROVED, 9=INVALID
       - score (FLOAT, DEFAULT 0) - оценка качества разрешения (10*близость_value + сумма weight совпавших элементов)
       - created_at (TIMESTAMP, NOT NULL)
       - updated_at (TIMESTAMP, NOT NULL)
       - scope_id (INTEGER, FOREIGN KEY -> scopes.id, NOT NULL, DEFAULT 0)

       Индексы:
       - UNIQUE(occurrence_id, correct_object_id) - уникальность пары (Occurrence, CorrectObject)
       - INDEX(occurrence_id) - для быстрого поиска всех Resolution для Occurrence
       - INDEX(correct_object_id) - для быстрого поиска всех Resolution для CorrectObject
       - INDEX(occurrence_id, status) - для поиска Resolution по Occurrence и статусу (особенно APPROVED)
       - INDEX(scope_id) - для фильтрации по области действия
       - INDEX(status) WHERE status != 9 - для поиска активных Resolution (не INVALID)
       - INDEX(occurrence_id, score) WHERE status != 9 - для поиска лучшего Resolution по score

    Дополнительные ограничения:
    - CASCADE DELETE: при удалении Occurrence удаляются связанные Resolution
    - CASCADE DELETE: при удалении CorrectObject удаляются связанные Resolution
    - CASCADE DELETE: при удалении Scope удаляются связанные Occurrence, CorrectObject, Resolution (или RESTRICT, в зависимости от бизнес-логики)
    - CHECK: для каждого occurrence_id максимум один Resolution со status=1 (APPROVED)
    - CHECK: status IN (0, 1, 9)

    Триггеры/События:
    - При изменении любого CorrectObject в scope обновлять scopes.updated_at для этого scope_id
    - При изменении scopes.updated_at инвалидировать кеши resolved_to для всех Occurrence в этом scope (помечать как требующие пересчета)

    Альтернативный вариант хранения контекста (если JSON не поддерживается):
    - Отдельная таблица `context_elements` с полями: id, parent_type (occurrence/correct_object), parent_id, key, value, important, weight, absence_allowed
    - Индексы: INDEX(parent_type, parent_id) для быстрого доступа к элементам контекста объекта


    ВИЗУАЛЬНАЯ ЧАСТЬ:
    
    Таблица Resolution, колонки:
     - Occurrence (value),
     - статус (PENDING/APPROVED/INVALID): значок-символ + цвет,
     - CorrectObject (value),
     - required_context_elements (кратко),
     - действие (подтверждение/аннулирование/редактирование/удаление/переключение на другой CorrectObject/отделение от этого CorrectObject в самостоятельный новый CorrectObject).

    Цвета: PENDING - красный, APPROVED - зелёный/чёрный, INVALID - серый.
     Дополнительно цветом будут помечаться случаи неразрешённых "дублей": когда один Occurrence разрешается в несколько CorrectObject в статусе PENDING (и не назначено ни одного APPROVED для этого Occurrence).

    Сортировка таблицы: по обоим value, датам создания / обновления Occurrence / Resolution / CorrectObject. Фильтрация по статусу Resolution (PENDING/APPROVED/INVALID).
    
    Форма редактирования: Occurrence (просмотр), CorrectObject (редактирование), required_context_elements (настройка absence_allowed и score).
    Моноширинный текст с подсветкой невидимых символов, пример реализации: https://den1s0v.github.io/regex-helper/src/


    ВОПРОСЫ ДЛЯ УТОЧНЕНИЯ ПРИ РЕАЛИЗАЦИИ:

    1. АЛГОРИТМЫ И ВЫЧИСЛЕНИЯ: [ОТВЕТЫ ДАНЫ, ИНФОРМАЦИЯ ПЕРЕНЕСЕНА В ОСНОВНОЙ ТЕКСТ]


    2. БИЗНЕС-ЛОГИКА:
       - Обработка неоднозначностей в UI:
         * Как отображать случаи, когда один Occurrence имеет несколько PENDING Resolution?
         * Нужны ли уведомления/алерты для администратора?
         * Автоматическое разрешение или всегда требуется ручное вмешательство?

       - Создание Resolution вручную:
         * Может ли администратор создать Resolution с INVALID статусом?
         * Что происходит при создании Resolution вручную, если автоматическое создание запрещено (INVALID для прямого Resolution)?
         * Можно ли редактировать автоматически созданные Resolution?

       - Удаление объектов:
         * Мягкое удаление (soft delete) или жесткое удаление?
         * Нужна ли история изменений (audit log)?
         * Что происходит с Resolution при удалении Occurrence/CorrectObject?

    3. API И ИНТЕГРАЦИЯ:
       - API endpoints:
         * REST API или GraphQL?
         * Какие endpoints нужны? (CRUD для всех сущностей, bulk операции, поиск?)
         * Нужна ли пагинация, фильтрация, сортировка?

       - Аутентификация и авторизация:
         * Какая система аутентификации? (JWT, session-based, OAuth?)
         * Нужны ли роли пользователей? (администратор, ревьювер, только просмотр?)
         * Права доступа по scope_id (изоляция данных между клиентами)?

       - Внешние интеграции:
         * Как происходит синхронизация с внешними справочниками? (по external_id)
         * Нужен ли импорт/экспорт данных?
         * Webhooks или другие механизмы уведомлений?

    4. ПРОИЗВОДИТЕЛЬНОСТЬ И ОПТИМИЗАЦИЯ:
       - Масштабирование:
         * Ожидаемый объем данных? (количество Occurrence, CorrectObject, Resolution)
         * Нужна ли поддержка массовых операций (bulk create/update)?
         * Требования к производительности apply_correction?

       - Кеширование:
         * Нужен ли Redis/Memcached для кеширования?
         * Какие данные кешировать? (resolved_to, результаты поиска?)
         * Стратегия инвалидации кеша?

       - Фоновые задачи:
         * Нужны ли Celery/другие задачи для:
           - Автоматического пересчета resolved_to
           - Очистки устаревших Resolution
           - Синхронизации с внешними системами?

    5. ВАЛИДАЦИЯ И ОБРАБОТКА ОШИБОК:
       - Валидация данных:
         * Ограничения на длину value, key, value в ContextElement?
         * Валидация формата JSON для context и required_context_elements?
         * Проверка уникальности при создании/обновлении?

       - Обработка ошибок:
         * Что возвращать при отсутствии Resolution? (None, исключение, дефолтное значение?)
         * Как обрабатывать конфликты при одновременном редактировании?
         * Нужны ли транзакции для атомарных операций?

    6. ТЕСТИРОВАНИЕ:
       - Какие сценарии критичны для тестирования?
       - Нужны ли тестовые данные/фикстуры?
       - Требования к покрытию тестами?

    7. ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ:
       - Статистика и аналитика:
         * Нужны ли отчеты? (количество неразрешенных Occurrence, эффективность Resolution и т.д.)
         * Дашборды для администратора?

       - Версионирование:
         * Нужна ли история изменений Resolution/CorrectObject?
         * Возможность отката изменений?

       - Экспорт/импорт:
         * Форматы экспорта? (JSON, CSV, Excel?)
         * Массовый импорт данных?

"""

from typing import Optional
from datetime import datetime


class Item:
    """Базовый класс для корректируемых объектов/сущностей.
        Базовый класс для Occurrence и CorrectObject.
        Объекты с одинаковым `value`, но разными важными элементами контекста считаются разными.
    """
    value: str
    context: list['ContextElement']
    score: Optional[float] = 1
    approved: bool = False
    manual: bool = False
    scope_id: int = 0
    updated_at: datetime  # дата последнего изменения / кеширования resolved_to


class Occurrence(Item):
    """Вхождение — входной объект из слоя входных данных (необработанные данные).
        Может иметь несколько Resolution (один-ко-многим).
    """
    resolved_to: Optional['CorrectObject'] = None  # кеш, пересчитывается после любого изменения с любыми CorrectObject в БД.


class CorrectObject(Item):
    """Корректный логический объект из слоя корректировок.
        Хранит required_context_elements для проверки соответствия Occurrence.
        Resolution не создается, если нет совпадения (с учетом absence_allowed).
        Уникальность: по ID (если указан) или по value (если required_context_elements пуст).
        Resolution → CorrectObject: многие-к-одному.
    """
    id: Optional[str] = None
    required_context_elements: list['ContextElement']
    name: Optional[str] = None
    description: Optional[str] = None


class ContextElement:
    """Элемент контекста (ключ-значение).
        important: если True - при несовпадении значений Resolution не создается; если False - создается, но score меньше.
        weight: вес элемента для вычисления score Resolution (используется в формуле: сумма weight совпавших элементов).
        absence_allowed: если True - отсутствие элемента допускается (score меньше); если False - отсутствие запрещает создание Resolution.
    """
    key: str
    value: str
    important: bool = False
    weight: Optional[float] = 1  # Вес для вычисления score Resolution
    absence_allowed: bool = False


class Resolution:
    """Разрешение: связь Occurrence → CorrectObject.
        Создается автоматически только при совпадении required_context_elements (с учетом absence_allowed), вручную - между любыми.
        Статусы: PENDING (ожидает проверки), APPROVED (утверждено), INVALID (аннулировано).
        Возвращает CorrectObject в статусах PENDING и APPROVED.
    """
    occurrence: Occurrence
    correct_object: CorrectObject
    manual: bool = False
    status: int = 0  # 0=PENDING, 1=APPROVED, 9=INVALID
    score: Optional[float] = 0
    created_at: datetime = 0
    updated_at: datetime = 0
    scope_id: int = 0


# Функции для работы с Resolution

def find_or_create_correct_object(
    value: str,
    object_id: Optional[str] = None,
    name: Optional[str] = None,
    description: Optional[str] = None,
    required_context_elements: Optional[list['ContextElement']] = None,
) -> CorrectObject:
    """Поиск или создание CorrectObject с проверкой дубликатов.
    Ключ поиска: object_id (приоритет) или value + required_context_elements.
    """
    pass


def split_resolution(resolution: Resolution, new_correct_object: CorrectObject) -> Resolution:
    """Создает новое Resolution для того же Occurrence с другим CorrectObject."""
    pass


def merge_resolutions(resolution1: Resolution, resolution2: Resolution, target_correct_object: CorrectObject) -> Resolution:
    """Объединяет два Resolution (одного Occurrence) в одно с указанным CorrectObject."""
    pass


# Ключевая функция API корректировок.
def apply_correction(occurrence: Occurrence, scope_id: int = 0) -> CorrectObject:
    """Возвращает CorrectObject для заданного Occurrence.
    
      Алгоритм:
    # 0. Для поданного Occurrence: найти в БД или добавить в БД, если существующие не покрывают:
    	- отобрать все существуюшие Occurrence с совпадающим value,
    	- из найденных отобрать те, чьи элементы контекста покрывают переданные: все значения присутствуют, и значения равны,
		- если таковых нет, то добавить в БД как новый (и дальше работать с ним);
    	- при обнаружении нескольких брать тот, у которого меньше отличий по составу контекста, или иначе любой (и дальше работать с ним).

    # 1. Найти существующее Resolution для Occurrence:
    	есть APPROVED → вернуть её,
    	иначе проверить, есть ли в resolved_to закишированный и актуальный по дате результат: если есть, то вернуть его.

    # 2. Если не найдено - выполнить анализ и:
    	- найти подходящие CorrectObject (проверка required_context_elements с учетом absence_allowed) учитывая и не изменяя существующие INVALID,
    	- создать для несуществующих новые Resolution со статусом PENDING, сохранить их,
    	- удалить из БД возможные старые Resolution для этого Occurrence, которые больше не корректны, т.е. не отражают допустимый способ разрешения входящего объекта.

    # 3. Найти лучшую по score Resolution (из тех, что не INVALID) для этого Occurrence, закешировать результат в resolved_to и задать дату обновления и вернуть её CorrectObject, если найдено.

    # 4. Если не найдено - создать новый CorrectObject (на основе Occurrence и всех его элементов контекста в статусе important) и соответствующий Resolution (если только уже нет явно заданного INVALID для прямого Resolution, т.е. такое преобразоавние явно запрещено администратором).

    # 5. Вернуть CorrectObject или ничего, если не удалось ничего создать и связать в статусе не-INVALID.
    """
    pass
