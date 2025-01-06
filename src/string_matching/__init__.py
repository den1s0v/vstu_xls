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
from string_matching.StringMatch import StringMatch
from string_matching.StringPattern import StringPattern

from string_matching.helper_transformers import shrink_extra_inner_spaces, fix_sparse_words

from string_matching.CellClassifier import CellClassifier


def read_cell_types(config_file: str = '../cnf/cell_types.yml', data=None) -> Dict[str, CellType]:
    if not data:
        with open(config_file, encoding='utf-8') as f:
            data = yaml.safe_load(f)

    assert isinstance(data, dict), data

    try:
        cell_types_list = data['cell_types']
    except KeyError:
        raise ValueError('Format error: `cell_types` key expected.')

    cell_types = {}
    for kt in cell_types_list:
        for k, t in kt.items():
            cell_types[k] = CellType(name=k, **t)

    return cell_types



