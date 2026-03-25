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

from pathlib import Path

import yaml

from vstuxls.string_matching.CellClassifier import CellClassifier
from vstuxls.string_matching.CellType import CellType
from vstuxls.string_matching.helper_transformers import fix_sparse_words, shrink_extra_inner_spaces
from vstuxls.string_matching.StringMatch import StringMatch
from vstuxls.string_matching.StringPattern import StringPattern
from vstuxls.utils import find_file_under_path


def read_cell_types(
    config_file: str = "../cnf/cell_types.yml",
    data: dict | None=None,
    raise_on_error=True,
    base_dir: 'str | Path | None' = None,
) -> dict[str, CellType] | None:
    if not data:
        assert config_file
        config_file = find_file_under_path(config_file, base_dir or '.')
        with open(config_file, encoding="utf-8") as f:
            data = yaml.safe_load(f)

    assert isinstance(data, dict), data

    if "cell_types" in data:
        # found key for data, get it
        cell_types_list = data["cell_types"]
    elif "cell_types_filepath" in data:
        # look for data in specified file
        filepath = data["cell_types_filepath"]
        # Note: uncontrolled recursion
        return read_cell_types(filepath, base_dir=base_dir)
    elif raise_on_error:
        raise ValueError(
            f"Format error: `cell_types` or `cell_types_filepath` key expected in given file: `{config_file}`."
        )
    else:
        return None

    cell_types = {}
    for kt in cell_types_list:
        for k, t in kt.items():
            cell_types[k] = CellType(name=k, **t)

    return cell_types
