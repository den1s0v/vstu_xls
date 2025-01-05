import string_matching as ns
from string_matching.CellType import CellType
from string_matching.StringMatch import StringMatch


from typing import List


class CellClassifier:
    """ Классификатор для контента ячейки,
        находит для данной строки наиболее подходящие типы
        из известных CellType """
    cell_types: List[CellType]

    def __init__(self, cell_types=None):
        if not cell_types:
            cell_types = ns.read_cell_types().values()
        self.cell_types = list(cell_types)

    def match(self, cell_text: str, limit=None) -> List[StringMatch]:
        """ Find matches for given `cell_text`, sorted by precision DESC.
         Optionally crop result to `limit` best matches. """
        matches = []
        for ct in self.cell_types:
            if m := ct.match(cell_text):
                matches.append(m)

        matches.sort(key=lambda m: m.precision, reverse=True)  # Changed confidence → precision
        return matches[:limit]
