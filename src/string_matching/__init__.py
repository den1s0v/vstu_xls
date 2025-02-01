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
from string_matching.CellClassifier import CellClassifier
from string_matching.CellType import CellType
from string_matching.StringMatch import StringMatch
from string_matching.StringPattern import StringPattern

from string_matching.helper_transformers import shrink_extra_inner_spaces, fix_sparse_words
from string_matching import CellClassifier
from utils import find_file_under_path


def read_cell_types(config_file: str = '../cnf/cell_types.yml', data=None) -> Dict[str, CellType]:
    if not data:
        assert config_file
        config_file = find_file_under_path(config_file)
        with open(config_file, encoding='utf-8') as f:
            data = yaml.safe_load(f)

    assert isinstance(data, dict), data

    if 'cell_types' in data:
        # found key for data, get it
        cell_types_list = data['cell_types']
    elif 'cell_types_filepath' in data:
        # look for data in specified file
        filepath = data['cell_types_filepath']
        # Note: uncontrolled recursion
        return read_cell_types(filepath)
    else:
        raise ValueError(
            f'Format error: `cell_types` or `cell_types_filepath` key expected in given file: `{config_file}`.')

    cell_types = {}
    for kt in cell_types_list:
        for k, t in kt.items():
            cell_types[k] = CellType(name=k, **t)

    return cell_types



