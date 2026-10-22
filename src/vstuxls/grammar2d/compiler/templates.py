"""Шаблоны/параметры грамматики (DSL v2): убирают копипасту однотипных паттернов.

Пример (в корне файла грамматики)::

    templates:
      lesson_frame_1_group:
        name: 'lesson_frame_1_group_${hours}h_${marker}'
        params:
          hours: [2, 4, 6]
          marker: [explicit, assumed]
        exclude:
          - {hours: 2, marker: assumed}   # необязательно: комбинации, которые не нужно порождать
        body:
          kind: area
          size: '2+ x ${hours * 3 // 2}'
          ...

Каждая комбинация параметров (декартово произведение) порождает паттерн с подстановкой `${...}`.
Выражения внутри `${}` — безопасная арифметика (см. `safe_eval`).
"""

from __future__ import annotations

import ast
import itertools
import operator
import re
from typing import Any

from vstuxls.grammar2d.compiler.diagnostics import DiagnosticReport, SourceLoc
from vstuxls.grammar2d.compiler.source import LocDict, loc_of

_BIN = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod, ast.Div: operator.truediv, ast.Pow: operator.pow,
}
_CMP = {
    ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt, ast.LtE: operator.le,
    ast.Gt: operator.gt, ast.GtE: operator.ge,
}
_FUNCS = {'min': min, 'max': max, 'abs': abs, 'str': str, 'int': int}

_PLACEHOLDER = re.compile(r'\$\{([^{}]+)\}')


def safe_eval(expr: str, env: dict[str, Any]) -> Any:
    """Вычислить арифметическое/логическое выражение без доступа к атрибутам и импортам."""

    def ev(node):
        if isinstance(node, ast.Expression):
            return ev(node.body)
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            raise NameError(f'unknown parameter `{node.id}`')
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN:
            return _BIN[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp):
            v = ev(node.operand)
            if isinstance(node.op, ast.USub):
                return -v
            if isinstance(node.op, ast.UAdd):
                return +v
            if isinstance(node.op, ast.Not):
                return not v
        if isinstance(node, ast.BoolOp):
            vals = [ev(v) for v in node.values]
            return all(vals) if isinstance(node.op, ast.And) else any(vals)
        if isinstance(node, ast.Compare):
            left = ev(node.left)
            for op, comp in zip(node.ops, node.comparators):
                right = ev(comp)
                if type(op) not in _CMP or not _CMP[type(op)](left, right):
                    return False
                left = right
            return True
        if isinstance(node, ast.IfExp):
            return ev(node.body) if ev(node.test) else ev(node.orelse)
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in _FUNCS and not node.keywords):
            return _FUNCS[node.func.id](*(ev(a) for a in node.args))
        raise ValueError(f'unsupported expression element: {ast.dump(node)[:60]}')

    return ev(ast.parse(expr.strip(), mode='eval'))


def substitute(value: Any, env: dict[str, Any]) -> Any:
    """Рекурсивно подставить `${expr}` в строки, ключи и вложенные структуры."""
    if isinstance(value, str):
        m = _PLACEHOLDER.fullmatch(value.strip())
        if m:
            return safe_eval(m.group(1), env)
        return _PLACEHOLDER.sub(lambda mm: str(safe_eval(mm.group(1), env)), value)
    if isinstance(value, LocDict):
        out = LocDict()
        out.file, out.line = value.file, value.line
        for k, v in value.items():
            nk = substitute(k, env) if isinstance(k, str) else k
            out[nk] = substitute(v, env)
            out.key_lines[nk] = value.key_lines.get(k, value.line)
        return out
    if isinstance(value, dict):
        return {(substitute(k, env) if isinstance(k, str) else k): substitute(v, env) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute(v, env) for v in value]
    return value


def _as_list(v) -> list:
    return list(v) if isinstance(v, (list, tuple)) else [v]


def _matches(combo: dict, pattern: dict) -> bool:
    return all(combo.get(k) == v for k, v in pattern.items())


def expand_template(tpl_name: str, tpl: Any, report: DiagnosticReport) -> list[tuple[str, LocDict]]:
    """Развернуть один шаблон в список `(имя_паттерна, тело)`."""
    loc = loc_of(tpl)
    if not isinstance(tpl, dict) or 'body' not in tpl or 'name' not in tpl:
        report.add('G016', f'шаблон `{tpl_name}` должен содержать ключи `name` и `body`', loc=loc)
        return []

    params = tpl.get('params') or {}
    if not isinstance(params, dict):
        report.add('G016', f'шаблон `{tpl_name}`: `params` должен быть словарём', loc=loc)
        return []

    keys = list(params.keys())
    value_lists = [_as_list(params[k]) for k in keys]
    excludes = tpl.get('exclude') or []
    when = tpl.get('when')

    result: list[tuple[str, LocDict]] = []
    for values in itertools.product(*value_lists):
        combo = dict(zip(keys, values))
        if any(isinstance(ex, dict) and _matches(combo, ex) for ex in excludes):
            continue
        try:
            if when is not None and not safe_eval(str(when), combo):
                continue
            name = substitute(tpl['name'], combo)
            body = substitute(tpl['body'], combo)
        except Exception as e:  # noqa: BLE001 - любая ошибка подстановки = диагностика
            report.add('G016', f'шаблон `{tpl_name}` {combo}: {e}', loc=loc)
            continue
        if not isinstance(body, LocDict):
            report.add('G016', f'шаблон `{tpl_name}`: `body` должен быть словарём', loc=loc)
            continue
        body['_origin'] = f'template:{tpl_name}'
        result.append((str(name), body))
    if not result:
        report.add('G016', f'шаблон `{tpl_name}` не породил ни одного паттерна', loc=loc)
    return result


def expand_instance(name: str, raw: LocDict, templates: dict[str, Any], report: DiagnosticReport) -> LocDict | None:
    """Паттерн вида `{template: tpl_name, args: {...}}` -> тело шаблона с подставленными аргументами."""
    tpl_name = raw.get('template')
    args = raw.get('args') or {}
    tpl = templates.get(tpl_name)
    if tpl is None or not isinstance(tpl, dict) or 'body' not in tpl:
        report.add('G016', f'паттерн `{name}` ссылается на неизвестный шаблон `{tpl_name}`', pattern=name,
                   loc=loc_of(raw, 'template'))
        return None
    try:
        body = substitute(tpl['body'], dict(args))
    except Exception as e:  # noqa: BLE001
        report.add('G016', f'паттерн `{name}`: {e}', pattern=name, loc=loc_of(raw, 'args'))
        return None
    if isinstance(body, LocDict):
        body['_origin'] = f'template:{tpl_name}'
    return body


def loc_for(data, key=None) -> SourceLoc:
    return loc_of(data, key)
