"""Загрузка YAML с сохранением номеров строк (для диагностик с положением в файле)."""

from __future__ import annotations

from pathlib import Path

import yaml

from vstuxls.grammar2d.compiler.diagnostics import SourceLoc


class LocDict(dict):
    """`dict`, помнящий строку начала самого отображения и строки каждого ключа."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.file: str | None = None
        self.line: int | None = None
        self.key_lines: dict = {}

    def loc_of(self, key=None) -> SourceLoc:
        line = self.key_lines.get(key, self.line) if key is not None else self.line
        return SourceLoc(self.file, line)

    def shallow_copy(self) -> 'LocDict':
        c = LocDict(self)
        c.file, c.line, c.key_lines = self.file, self.line, dict(self.key_lines)
        return c


def loc_of(data, key=None, default: SourceLoc | None = None) -> SourceLoc:
    """Положение ключа (или всего отображения) для любого объекта; безопасно для обычных `dict`."""
    if isinstance(data, LocDict):
        return data.loc_of(key)
    return default or SourceLoc()


class _LocLoader(yaml.SafeLoader):
    file_name: str | None = None


def _construct_loc_map(loader: _LocLoader, node: yaml.MappingNode):
    data = LocDict()
    yield data
    data.file = loader.file_name
    data.line = node.start_mark.line + 1
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=True)
        value = loader.construct_object(value_node, deep=True)
        data[key] = value
        data.key_lines[key] = key_node.start_mark.line + 1


_LocLoader.add_constructor('tag:yaml.org,2002:map', _construct_loc_map)


def load_yaml_text(text: str, file_name: str | None = None):
    """Разобрать YAML из строки. Отображения возвращаются как `LocDict`."""
    loader = _LocLoader(text)
    loader.file_name = file_name
    try:
        return loader.get_single_data()
    finally:
        loader.dispose()


def load_yaml_file(path: str | Path):
    path = Path(path)
    with open(path, encoding='utf-8') as f:
        return load_yaml_text(f.read(), str(path))
