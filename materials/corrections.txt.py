"""Набросок структуры программы и API для автоматического повторения ручных корректировок данных, преимущественно строковых.
    Полезно для тех алгоритмов, которые регулярно обрабатывают одни и те же / сильно похожие данные.

    АРХИТЕКТУРА:
    
    Двухслойная модель:
    - Слой входных данных: Occurrence (вхождения, необработанные данные)
    - Слой корректировок: CorrectObject (корректные объекты с ID из справочников)
    - Разрешение/привязка: Resolution (связь между слоями)
    
    Связи: Occurrence → Resolution (один-ко-многим), Resolution → CorrectObject (многие-к-одному)
    
    МЕХАНИЗМ РАЗРЕШЕНИЯ:
    
    CorrectObject хранит required_context_elements (обязательные элементы контекста). Resolution создается автоматически со статусом PENDING и только при совпадении элементов контекста:
    - Элемент присутствует в Occurrence и значения совпадают → СООТВЕТСТВУЕТ
    - Элемент отсутствует в Occurrence, проверяем absence_allowed элемента контекста:
      * absence_allowed=True → СООТВЕТСТВУЕТ (тип может быть неизвестен заранее)
      * absence_allowed=False → НЕ СООТВЕТСТВУЕТ (тип должен быть известен заранее)

    "Разрешение" может быть переопределено вручную для любой пары (в т.ч. создано без оглядки на контекст, или переназначено, или удалено).
    APPROVED может быть назначено для каждого Occurrence максимум 1 раз и имеет приоритет над остальными статусами.
    Если APPROVED не задан, то выбирается CorrectObject со статусом PENDING; при наличии нескольких соответствий возникает ситуация неоднозначности; до её разрешения человеком вычисляется score для каждого resolution как 10*(оценка нечёткой близости по value) + взвешенная сумма совпавших элементов контекста, и выбирается наилучшее; при совпадении оценок выбирается первое по списку.
    Явный INVALID не участвует в выборе корректного объекта.
    При отсутствии подходящего корректного объекта для Occurrence создается новый CorrectObject без изменения содержимого.
    
    УНИКАЛЬНОСТЬ:
    - Occurrence: по value и перечню required_context_elements: новый не добавляется, если уже существует такой, набор элементов контекста которого полностью покрывает элементы контекста кандидата.
    - CorrectObject: по ID (если указан) или по value + required_context_elements.
    - Resolution: по паре (Occurrence, CorrectObject).


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


class Occurrence(Item):
    """Вхождение — входной объект из слоя входных данных (необработанные данные).
        Может иметь несколько Resolution (один-ко-многим).
    """
    status: Optional[int] = None


class CorrectObject(Item):
    """Корректный логический объект из слоя корректировок.
        Хранит required_context_elements для проверки соответствия Occurrence.
        Resolution не создается, если нет совпадения (с учетом absence_allowed).
        Уникальность: по ID (если указан) или по value (если required_context_elements пуст).
        Resolution → CorrectObject: многие-к-одному.
    """
    id: Optional[str] = None
    required_context_elements: list[ContextElement]
    name: Optional[str] = None
    description: Optional[str] = None


class ContextElement:
    """Элемент контекста (ключ-значение).
        important: важность для определения гипотезы.
        absence_allowed: разрешено ли отсутствие при проверке соответствия (True - тип может быть неизвестен, False - тип должен быть известен).
    """
    key: str
    value: str
    important: bool = False
    score: Optional[float] = 1
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
    1. Найти существующее Resolution для Occurrence (APPROVED → вернуть, PENDING → вернуть, только INVALID → пересоздать заново если не создано, иначе ничего не вернуть)
    2. Если не найдено - найти подходящий CorrectObject (проверка required_context_elements с учетом absence_allowed)
    3. Если найден - создать/использовать Resolution для пары (Occurrence, CorrectObject)
    4. Если не найден - создать новый CorrectObject (на основе important элементов контекста) и Resolution
    5. Вернуть CorrectObject
    """
    pass
