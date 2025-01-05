from typing import List
from typing import Optional

from string_matching.StringPattern import RE_COMMON_SEPARATOR
from string_matching.StringMatch import StringMatch
from string_matching.StringPattern import StringPattern


VALID_update_content = {'clear', 'replace_with_preprocessed'}


class CellType:
    """ Класс (разновидность) контента ячейки,
        характеризующийся собственным набором паттернов.

        Каждый паттерн является альтернативой остальным и может по-своему интерпретировать содержимое.
        Паттерн может находить несколько смысловых величин в одной текстовой строке
        (хотя это и не нужно в большинстве случаев,
        иногда в одной ячейке содержатся данные из разных ячеек, просто разделённые пробелами).

        `update_content`: optional names of transformations to apply on content saved in match object.
        Available so far: 'clear', 'replace_with_preprocessed'.
    """
    name: str  # id-like name
    description: str  # comment for human
    patterns: List[StringPattern]  # patterns with confidence level
    update_content: list[str] = ()  # optional names of transformations to apply to content

    def __init__(self, name='a', description='no info', patterns=None, update_content=None):
        self.name = name
        self.description = description
        self.patterns = self.prepare_patterns(patterns, self)

        if update_content is not None and isinstance(update_content, str):
            self.update_content = RE_COMMON_SEPARATOR.split(update_content)

        assert not (set(self.update_content or ()) - VALID_update_content), f"CellType.update_content must contain one or more of {VALID_update_content}, got: `{self.update_content}`."

    @classmethod
    def prepare_patterns(cls, patterns, content_class, transformations=None):
        assert patterns, 'at least one pattern is required'
        if isinstance(patterns, StringPattern):
            return [patterns]
        if isinstance(patterns, str):
            return [StringPattern(patterns)]

        ps = [
            p if isinstance(p, StringPattern) else StringPattern(**p, content_class=content_class)
            for p in patterns
        ]
        ps.sort(key=lambda p: p.confidence, reverse=True)
        return ps

    def match(self, cell_text: str) -> Optional[StringMatch]:
        """Return match according to pattern with the highest confidence."""
        for p in self.patterns:
            if m := p.match(cell_text):
                return m
        return None
