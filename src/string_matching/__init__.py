# confidence_matching.py

"""
При классификации строк может понадобиться
    определять степень уверенности в том,
    насколько данная строка подходит к
    заданному классу,
    то есть определять степень уверенности
    (в точности классификации).

     Для этого каждому классу сопоставляется
     несколько регулярных выражений,
     каждое из которых разработано для своего
     уровня уверенности,
     обычно от большего к меньшему -- от 1 до 0.1
     (уровень уверенности, равный нулю, не имеет смысла).
"""
from typing import Dict, Optional, Union

import yaml

from adict import adict
from string_matching.CellType import CellType
from string_matching.StringPattern import StringPattern

from string_matching.helper_transformers import shrink_extra_inner_spaces, fix_sparse_words

from string_matching.CellClassifier import CellClassifier


def read_cell_types(config_file: str = '../cnf/cell_types.yml') -> Dict[str, CellType]:
    with open(config_file, encoding='utf-8') as f:
        data = yaml.safe_load(f)

    cell_types = {}
    for kt in data['cell_types']:
        for k, t in kt.items():
            cell_types[k] = CellType(name=k, **t)

    return cell_types



