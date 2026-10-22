"""Frontend: YAML (v1 и v2) -> IR + структурированные диагностики.

В отличие от старого `read_grammar`, фронтенд:

* **ничего не теряет молча** — каждая проблема (неизвестный kind/ключ, битый диапазон,
  отсутствующий файл) становится диагностикой с положением в YAML;
* понимает расширения DSL v2: `alt/one_of`, `require/forbid`, `relations`, `align`,
  `templates`, `count`, `policies`, `import`;
* сохраняет старые грамматики v1 без изменений (`kind: general` + `extends`, `overlap`, ...).
"""

from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from vstuxls.constraints_2d.LocationConstraint import LocationConstraint
from vstuxls.geom2d import open_range, parse_size_range
from vstuxls.grammar2d.compiler.diagnostics import DiagnosticReport, SourceLoc
from vstuxls.grammar2d.compiler.ir import (
    OPPOSITE, SIDES, ArrayIR, CellTypeIR, ComponentIR, EdgeRef, GrammarIR, LocationIR, OverlapPolicy,
    PatternIR, PKind, PolicyIR, RelationIR, Role, StringPatternIR, axis_of,
)
from vstuxls.grammar2d.compiler.source import LocDict, load_yaml_file, load_yaml_text, loc_of
from vstuxls.grammar2d.compiler.templates import expand_instance, expand_template
from vstuxls.utils import find_file_under_path

ARRAY_DIRECTIONS = ('row', 'column', 'auto', 'fill')
ARRAY_ALIGNS = ('both', 'start', 'end', 'none')
DISTANCE_KINDS = ('corner', 'side')
OVERLAP_MODES = ('none', 'full', 'partial')
OVERLAP_METRICS = ('area', 'width', 'height', 'precision')
OVERLAP_ORDERS = ('max', 'min')

PATTERN_KEYS = {
    'kind', 'description', 'root', 'count_in_document', 'size', 'style', 'extends', 'static_data',
    'inner', 'outer', 'require', 'forbid', 'relations',
    'confidence', 'precision_threshold', 'overlap', 'allows_overlapping', 'priority', 'prefer', 'cost', 'policy',
    'content_type',
    'item_pattern', 'direction', 'item_count', 'gap', 'allow_breakdown', 'distance_kind', 'index_items', 'align',
    'one_of', 'template', 'args', 'inner_space_transparent', '_origin',
}
COMPONENT_KEYS = {
    'pattern', 'pattern_definition', 'location', 'size', 'weight', 'optional', 'precision_threshold',
    'count', 'description',
}
POLICY_KEYS = {'confidence', 'precision_threshold', 'overlap', 'allows_overlapping', 'exclusive',
               'priority', 'prefer', 'cost'}
ROOT_KEYS = {
    'grammar', 'root', 'target_mode', 'cell_types', 'cell_types_filepath', 'include_grammars', 'import',
    'patterns', 'templates', 'policies',
}

_REL_CMP = re.compile(
    r'^\s*(?P<a>\w+)\.(?P<ae>left|right|top|bottom)\s*(?P<op>==|<=|>=|<|>|=)\s*'
    r'(?P<b>\w+)\.(?P<be>left|right|top|bottom)\s*(?:(?P<sign>[+-])\s*(?P<n>\d+))?\s*$')
_REL_IN = re.compile(
    r'^\s*(?P<a>\w+)\.(?P<ae>left|right|top|bottom)\s*-\s*(?P<b>\w+)\.(?P<be>left|right|top|bottom)\s+in\s+(?P<r>.+?)\s*$')
_THIS_ALIASES = {'this', 'self', 'parent', 'element'}


@dataclass
class CompileResult:
    ir: GrammarIR
    report: DiagnosticReport


def _suggest(key: str, allowed: set[str]) -> str | None:
    m = difflib.get_close_matches(str(key), sorted(allowed), n=1, cutoff=0.6)
    return f'возможно, имелось в виду `{m[0]}`' if m else None


def to_range(value: Any) -> open_range:
    """Число / строка диапазона / open_range -> open_range (бросает ValueError)."""
    if isinstance(value, open_range):
        return value
    if isinstance(value, bool):
        raise ValueError(f'ожидался диапазон, получено {value!r}')
    if isinstance(value, (int, float)):
        return open_range(int(value), int(value))
    if isinstance(value, str):
        return open_range.parse(value)
    raise ValueError(f'ожидался диапазон, получено {value!r}')


class _Frontend:
    def __init__(self, report: DiagnosticReport):
        self.report = report
        self.ir = GrammarIR()
        self.raw_patterns: dict[str, LocDict] = {}
        self.raw_templates: dict[str, Any] = {}
        self.raw_policies: dict[str, Any] = {}
        self.visited: set[Path] = set()
        self.declared_root: str | None = None
        self.v2 = False  # диалект DSL v2 (`grammar: 2` в любом из файлов)

    # ------------------------------------------------------------------ документы
    def load_file(self, path: Path, require_cell_types: bool) -> None:
        resolved = path.resolve()
        if resolved in self.visited:
            self.report.add('G018', f'файл `{path}` уже загружен (повторный импорт/цикл пропущен)',
                            loc=SourceLoc(str(path)))
            return
        self.visited.add(resolved)
        self.ir.files.append(str(path))
        try:
            data = load_yaml_file(path)
        except Exception as e:  # noqa: BLE001
            self.report.add('G015', f'не удалось прочитать `{path}`: {e}', loc=SourceLoc(str(path)))
            return
        self.process_document(data, str(path), path.parent, require_cell_types)

    def process_document(self, data: Any, file_name: str, base_dir: Path, require_cell_types: bool) -> None:
        if not isinstance(data, dict):
            self.report.add('G015', 'корень файла грамматики должен быть словарём', loc=SourceLoc(file_name))
            return

        dialect = str(data.get('grammar', '1')).lower().lstrip('v').split('.')[0]
        if dialect == '2':
            self.v2 = True
            self.ir.dialect = 2
        for key in data:
            if key not in ROOT_KEYS:
                self.report.add('G005', f'неизвестный ключ верхнего уровня `{key}`',
                                loc=loc_of(data, key, SourceLoc(file_name)),
                                hint=_suggest(key, ROOT_KEYS))

        # --- типы ячеек
        if 'cell_types' in data:
            self._load_cell_types(data['cell_types'], file_name)
        elif 'cell_types_filepath' in data:
            ct_path = find_file_under_path(data['cell_types_filepath'], base_dir)
            if ct_path is None:
                self.report.add('G015', f'файл типов ячеек `{data["cell_types_filepath"]}` не найден',
                                loc=loc_of(data, 'cell_types_filepath', SourceLoc(file_name)))
            else:
                try:
                    ct_data = load_yaml_file(ct_path)
                    self.ir.files.append(str(ct_path))
                    if isinstance(ct_data, dict) and 'cell_types' in ct_data:
                        self._load_cell_types(ct_data['cell_types'], str(ct_path))
                    else:
                        self.report.add('G015', 'в файле типов ячеек ожидается ключ `cell_types`',
                                        loc=SourceLoc(str(ct_path)))
                except Exception as e:  # noqa: BLE001
                    self.report.add('G015', f'не удалось прочитать `{ct_path}`: {e}', loc=SourceLoc(str(ct_path)))

        # --- шаблоны, паттерны, политики
        templates = data.get('templates') or {}
        if isinstance(templates, dict):
            for tname, tpl in templates.items():
                self.raw_templates[tname] = tpl
        elif templates:
            self.report.add('G017', '`templates` должен быть словарём', loc=loc_of(data, 'templates'))

        patterns = data.get('patterns') or {}
        if isinstance(patterns, dict):
            for name, raw in patterns.items():
                self._register_raw(str(name), raw, loc_of(patterns, name, SourceLoc(file_name)))
        elif patterns:
            self.report.add('G017', '`patterns` должен быть словарём', loc=loc_of(data, 'patterns'))

        policies = data.get('policies') or {}
        if isinstance(policies, dict):
            for name, raw in policies.items():
                self.raw_policies[str(name)] = raw
        elif policies:
            self.report.add('G017', '`policies` должен быть словарём', loc=loc_of(data, 'policies'))

        if data.get('root'):
            self.declared_root = str(data['root'])
        if data.get('target_mode'):
            self.ir.target_mode = str(data['target_mode'])

        # --- импорты (после собственных паттернов: при дубликатах побеждает последний, как в v1)
        for key in ('include_grammars', 'import'):
            for sub in data.get(key) or ():
                sub_path = find_file_under_path(sub, base_dir)
                if sub_path is None:
                    self.report.add('G015', f'импортируемая грамматика `{sub}` не найдена',
                                    loc=loc_of(data, key, SourceLoc(file_name)))
                    continue
                self.load_file(sub_path, require_cell_types=False)

    def _register_raw(self, name: str, raw: Any, loc: SourceLoc) -> None:
        if not isinstance(raw, dict):
            self.report.add('G017', f'описание паттерна `{name}` должно быть словарём', pattern=name, loc=loc)
            return
        if name in self.raw_patterns:
            prev = self.raw_patterns[name]
            self.report.add('G009', f'паттерн `{name}` определён повторно; используется последнее определение',
                            pattern=name, loc=loc, related=[f'предыдущее определение: {loc_of(prev)}'])
        self.raw_patterns[name] = raw  # type: ignore[assignment]

    # ------------------------------------------------------------------ типы ячеек
    def _load_cell_types(self, items: Any, file_name: str) -> None:
        if not isinstance(items, list):
            self.report.add('G017', '`cell_types` должен быть списком', loc=SourceLoc(file_name))
            return
        for entry in items:
            if not isinstance(entry, dict):
                self.report.add('G017', 'элемент `cell_types` должен быть словарём', loc=SourceLoc(file_name))
                continue
            for name, spec in entry.items():
                loc = loc_of(entry, name, SourceLoc(file_name))
                if not isinstance(spec, dict):
                    self.report.add('G017', f'описание типа ячейки `{name}` должно быть словарём', loc=loc)
                    continue
                ct = CellTypeIR(
                    name=str(name),
                    description=str(spec.get('description', '')),
                    update_content=spec.get('update_content'),
                    loc=loc,
                    priority=int(spec.get('priority', 0) or 0),
                    except_types=[str(x) for x in (spec.get('except') or [])],
                    examples=[str(x) for x in (spec.get('examples') or [])],
                )
                plist = spec.get('patterns') or []
                if not plist:
                    self.report.add('G017', f'тип ячейки `{name}` не содержит паттернов', loc=loc)
                for p in plist:
                    if isinstance(p, str):
                        p = {'pattern': p}
                    if not isinstance(p, dict) or 'pattern' not in p:
                        self.report.add('G017', f'паттерн типа `{name}` должен содержать `pattern`', loc=loc)
                        continue
                    ct.patterns.append(StringPatternIR(dict(p), loc_of(p, 'pattern', loc)))
                if name in self.ir.cell_types:
                    self.report.add('G009', f'тип ячейки `{name}` определён повторно', loc=loc)
                self.ir.cell_types[str(name)] = ct

    # ------------------------------------------------------------------ сборка паттернов
    def build_all(self) -> None:
        # 1. шаблоны -> паттерны
        expanded: dict[str, LocDict] = {}
        for tname, tpl in self.raw_templates.items():
            for pname, body in expand_template(tname, tpl, self.report):
                if pname in self.raw_patterns or pname in expanded:
                    self.report.add('G009', f'паттерн `{pname}` (из шаблона `{tname}`) определён повторно',
                                    pattern=pname, loc=loc_of(tpl))
                expanded[pname] = body
        self.raw_patterns.update(expanded)

        # 2. инстансы `template: ...`
        for name in list(self.raw_patterns):
            raw = self.raw_patterns[name]
            if 'template' in raw:
                body = expand_instance(name, raw, self.raw_templates, self.report)
                if body is None:
                    del self.raw_patterns[name]
                else:
                    self.raw_patterns[name] = body

        # 3. паттерны
        for name, raw in self.raw_patterns.items():
            try:
                p = self.build_pattern(name, raw)
            except Exception as e:  # noqa: BLE001
                self.report.add('G017', f'не удалось разобрать паттерн `{name}`: {e}', pattern=name, loc=loc_of(raw))
                continue
            if p is not None:
                self.ir.patterns[name] = p

        # 4. политики из отдельной секции
        for name, raw in self.raw_policies.items():
            target = self.ir.patterns.get(name)
            loc = loc_of(raw)
            if target is None:
                self.report.add('POL002', f'политика задана для неизвестного паттерна `{name}`', pattern=name,
                                loc=loc)
                continue
            if not isinstance(raw, dict):
                self.report.add('G017', f'политика `{name}` должна быть словарём', pattern=name, loc=loc)
                continue
            target.policy = self._parse_policy(raw, name, loc, base=target.policy)
            self.ir.policies[name] = target.policy

        # 5. корень
        roots = [p.name for p in self.ir.patterns.values() if p.root]
        if self.declared_root:
            if self.declared_root not in self.ir.patterns:
                self.report.add('G010', f'корень `{self.declared_root}` не найден среди паттернов')
            else:
                roots = [self.declared_root] + [r for r in roots if r != self.declared_root]
        if roots:
            self.ir.root_name = roots[0]
            if len(set(roots)) > 1:
                self.report.add('G010', f'объявлено несколько корней: {sorted(set(roots))}', pattern=roots[0])
        self.ir.invalidate()

    def _check_keys(self, raw: dict, allowed: set[str], pattern: str | None, comp: str | None = None) -> list[str]:
        unknown = []
        for k in raw:
            if k not in allowed:
                unknown.append(str(k))
                self.report.add('G005', f'неизвестный ключ `{k}` игнорируется', pattern=pattern, component=comp,
                                loc=loc_of(raw, k), hint=_suggest(k, allowed))
        return unknown

    def _range(self, raw: dict, key: str, pattern: str, default: open_range | None = None,
               comp: str | None = None) -> open_range | None:
        if key not in raw:
            return default
        try:
            return to_range(raw[key])
        except Exception as e:  # noqa: BLE001
            self.report.add('G006', f'некорректный диапазон `{key}: {raw[key]!r}` ({e})', pattern=pattern,
                            component=comp, loc=loc_of(raw, key))
            return default

    def _size(self, raw: dict, pattern: str, comp: str | None = None):
        if 'size' not in raw or raw['size'] is None:
            return None
        try:
            return tuple(parse_size_range(str(raw['size'])))
        except Exception as e:  # noqa: BLE001
            self.report.add('G006', f'некорректный размер `size: {raw["size"]!r}` ({e})', pattern=pattern,
                            component=comp, loc=loc_of(raw, 'size'),
                            hint='формат: `W x H`, где W и H — диапазоны (`4+ x 1..2`)')
            return None

    def build_pattern(self, name: str, raw: dict, origin: str | None = None) -> PatternIR | None:
        loc = loc_of(raw)
        kind_value = raw.get('kind')
        if kind_value is None:
            self.report.add('G001', f'у паттерна `{name}` не указан `kind`', pattern=name, loc=loc)
            return None
        try:
            kind = PKind(str(kind_value))
        except ValueError:
            self.report.add('G001', f'неизвестный kind `{kind_value}`', pattern=name, loc=loc_of(raw, 'kind'),
                            hint='допустимо: ' + ', '.join(k.value for k in PKind))
            return None

        p = PatternIR(name=name, kind=kind, loc=loc, origin=origin or raw.get('_origin'))
        p.unknown_keys = self._check_keys(raw, PATTERN_KEYS, name)
        p.description = raw.get('description')
        p.root = bool(raw.get('root', False))
        p.style = raw.get('style')
        p.static_data = raw.get('static_data')
        p.count_in_document = self._range(raw, 'count_in_document', name, open_range(0, None))
        p.size = self._size(raw, name)

        ext = raw.get('extends') or []
        p.extends = [str(ext)] if isinstance(ext, str) else [str(e) for e in ext]

        p.policy = self._parse_policy(raw, name, loc)
        p.components = self._build_components(raw, name)
        p.relations = self._parse_relations(raw.get('relations'), name, loc_of(raw, 'relations'))
        if not self.v2:
            self._apply_v1_component_sizes(p)

        if kind is PKind.CELL:
            p.content_type = raw.get('content_type')
            if not p.content_type:
                self.report.add('G008', f'у терминала `{name}` не указан `content_type`', pattern=name, loc=loc)
        elif kind.is_array:
            p.array = self._build_array(raw, name)
        elif kind is PKind.ALT:
            one_of = raw.get('one_of') or []
            p.one_of = [str(one_of)] if isinstance(one_of, str) else [str(x) for x in one_of]
            if not p.one_of:
                self.report.add('G017', f'`alt` `{name}` без `one_of`', pattern=name, loc=loc)
        elif kind is PKind.AREA and not p.components:
            self.report.add('G017', f'у области `{name}` нет компонентов (`inner`/`outer`)', pattern=name, loc=loc)
        return p

    def _apply_v1_component_sizes(self, p: PatternIR) -> None:
        """Диалект v1: `size` у компонента ограничивает размер РОДИТЕЛЯ (так работал старый матчер).

        Переносим такие ограничения в `size` паттерна и предупреждаем; в v2 (`grammar: 2`) `size` компонента —
        размер самого компонента.
        """
        for c in p.components:
            if c.size is None:
                continue
            w, h = c.size
            self.report.add('G020', f'v1: `size: {w} x {h}` у компонента трактуется как размер родителя `{p.name}`',
                            pattern=p.name, component=c.name, loc=c.loc,
                            hint='перенесите в `size` паттерна; в диалекте v2 (`grammar: 2`) `size` компонента '
                                 'ограничивает сам компонент')
            if p.size is None:
                p.size = (w, h)
            else:
                nw, nh = p.size[0].intersect(w), p.size[1].intersect(h)
                if nw is None or nh is None:
                    self.report.add('G006', f'размеры компонентов несовместимы с размером паттерна `{p.name}`',
                                    pattern=p.name, component=c.name, loc=c.loc)
                else:
                    p.size = (nw, nh)
            c.size = None

    # ------------------------------------------------------------------ политика
    def _parse_policy(self, raw: dict, name: str, loc: SourceLoc, base: PolicyIR | None = None) -> PolicyIR:
        pol = PolicyIR(**{k: getattr(base, k) for k in
                          ('confidence', 'precision_threshold', 'overlap', 'exclusive_candidates',
                           'priority', 'prefer', 'cost')}) if base else PolicyIR()
        pol.loc = loc
        sources = [raw]
        nested = raw.get('policy')
        if isinstance(nested, dict):
            self._check_keys(nested, POLICY_KEYS, name)
            sources.append(nested)
        elif nested is not None:
            self.report.add('G017', '`policy` должен быть словарём', pattern=name, loc=loc_of(raw, 'policy'))

        for src in sources:
            if 'confidence' in src:
                try:
                    pol.confidence = float(src['confidence'])
                except (TypeError, ValueError):
                    self.report.add('G006', f'confidence `{src["confidence"]!r}` не число', pattern=name,
                                    loc=loc_of(src, 'confidence'))
            if 'precision_threshold' in src:
                try:
                    pol.precision_threshold = float(src['precision_threshold'])
                except (TypeError, ValueError):
                    self.report.add('G006', f'precision_threshold `{src["precision_threshold"]!r}` не число',
                                    pattern=name, loc=loc_of(src, 'precision_threshold'))
            if 'overlap' in src:
                pol.overlap = self._parse_overlap(src['overlap'], name, loc_of(src, 'overlap'))
            if 'allows_overlapping' in src:
                pol.exclusive_candidates = not bool(src['allows_overlapping'])
            if 'exclusive' in src:
                pol.exclusive_candidates = bool(src['exclusive'])
            if 'priority' in src:
                try:
                    pol.priority = int(src['priority'])
                except (TypeError, ValueError):
                    self.report.add('G006', f'priority `{src["priority"]!r}` не целое', pattern=name,
                                    loc=loc_of(src, 'priority'))
            if 'prefer' in src:
                pref = src['prefer']
                pol.prefer = [str(pref)] if isinstance(pref, str) else [str(x) for x in (pref or [])]
            if 'cost' in src:
                try:
                    pol.cost = float(src['cost'])
                except (TypeError, ValueError):
                    self.report.add('G006', f'cost `{src["cost"]!r}` не число', pattern=name,
                                    loc=loc_of(src, 'cost'))
        return pol

    def _parse_overlap(self, data: Any, name: str, loc: SourceLoc) -> OverlapPolicy | None:
        if not isinstance(data, dict):
            self.report.add('G006', 'секция `overlap` должна быть словарём', pattern=name, loc=loc)
            return None
        mode = str(data.get('mode', 'full'))
        if mode not in OVERLAP_MODES:
            self.report.add('G006', f'overlap.mode `{mode}` недопустим; допустимо {OVERLAP_MODES}',
                            pattern=name, loc=loc)
            mode = 'full'
        raw_resolution = data.get('resolution', ['area-max', 'precision-max'])
        criteria: list[tuple[str, str]] = []
        if not isinstance(raw_resolution, list):
            self.report.add('G006', 'overlap.resolution должен быть списком', pattern=name, loc=loc)
            raw_resolution = ['area-max', 'precision-max']
        for item in raw_resolution:
            parts = str(item).lower().split('-')
            if len(parts) != 2 or parts[0] not in OVERLAP_METRICS or parts[1] not in OVERLAP_ORDERS:
                self.report.add('G006', f'критерий overlap.resolution `{item}` недопустим',
                                pattern=name, loc=loc,
                                hint=f'формат `метрика-порядок`: метрики {OVERLAP_METRICS}, порядок {OVERLAP_ORDERS}')
                continue
            criteria.append((parts[0], parts[1]))
        if not criteria:
            criteria = [('area', 'max'), ('precision', 'max')]
        return OverlapPolicy(mode=mode, criteria=criteria)

    # ------------------------------------------------------------------ компоненты
    def _build_components(self, raw: dict, pname: str) -> list[ComponentIR]:
        components: list[ComponentIR] = []
        seen: dict[str, SourceLoc] = {}
        for section, role in (('inner', Role.INNER), ('outer', Role.OUTER),
                              ('require', Role.REQUIRE), ('forbid', Role.FORBID)):
            if section not in raw:
                continue
            data = raw[section]
            if not isinstance(data, dict):
                self.report.add('G017', f'секция `{section}` должна быть словарём', pattern=pname,
                                loc=loc_of(raw, section))
                continue
            for cname, cdata in data.items():
                cname = str(cname)
                cloc = loc_of(data, cname, loc_of(raw, section))
                if cname in seen:
                    self.report.add('G017', f'компонент `{cname}` объявлен повторно', pattern=pname, component=cname,
                                    loc=cloc, related=[f'первое объявление: {seen[cname]}'])
                    continue
                seen[cname] = cloc
                built = self._build_component(pname, cname, cdata, role, cloc)
                components.extend(built)
        return components

    def _build_component(self, pname: str, cname: str, cdata: Any, role: Role, loc: SourceLoc) -> list[ComponentIR]:
        if not isinstance(cdata, dict):
            self.report.add('G017', 'описание компонента должно быть словарём', pattern=pname, component=cname,
                            loc=loc)
            return []
        self._check_keys(cdata, COMPONENT_KEYS, pname, cname)

        comp = ComponentIR(name=cname, role=role, loc=loc)
        if 'pattern' in cdata:
            comp.pattern = str(cdata['pattern'])
        elif 'pattern_definition' in cdata:
            definition = cdata['pattern_definition']
            if not isinstance(definition, dict):
                self.report.add('G017', '`pattern_definition` должен быть словарём', pattern=pname, component=cname,
                                loc=loc_of(cdata, 'pattern_definition'))
                return []
            inline_name = f'{pname}.{cname}[inline]'
            inline = self.build_pattern(inline_name, definition, origin='inline')
            if inline is None:
                return []
            comp.pattern, comp.inline = inline_name, inline
            self.ir.patterns[inline_name] = inline
        else:
            self.report.add('G017', 'компонент не задаёт ни `pattern`, ни `pattern_definition`',
                            pattern=pname, component=cname, loc=loc)
            return []

        comp.location = self._parse_location(cdata, role, pname, cname)
        comp.size = self._size(cdata, pname, cname)
        for key, attr, conv in (('weight', 'weight', float), ('precision_threshold', 'precision_threshold', float)):
            if key in cdata:
                try:
                    setattr(comp, attr, conv(cdata[key]))
                except (TypeError, ValueError):
                    self.report.add('G006', f'`{key}: {cdata[key]!r}` не число', pattern=pname, component=cname,
                                    loc=loc_of(cdata, key))
        comp.optional = bool(cdata.get('optional', False))
        count = self._range(cdata, 'count', pname, None, cname)
        comp.count = count
        return self._expand_count(comp, pname)

    def _expand_count(self, comp: ComponentIR, pname: str) -> list[ComponentIR]:
        """Развернуть квантор `count: a..b` в `a` обязательных и `b-a` опциональных компонентов."""
        count = comp.count
        if count is None or (count.start == 1 and count.stop == 1):
            return [comp]
        if comp.is_predicate:
            self.report.add('G006', '`count` не применим к `require`/`forbid`', pattern=pname, component=comp.name,
                            loc=comp.loc)
            return [comp]
        lo = count.start or 0
        hi = count.stop
        if hi is None or hi > 12:
            self.report.add('G006', f'`count: {count}` слишком велик или не ограничен сверху',
                            pattern=pname, component=comp.name, loc=comp.loc,
                            hint='для неограниченного числа однотипных элементов используйте kind: array')
            return [comp]
        if hi == 0:
            return []
        out: list[ComponentIR] = []
        for i in range(hi):
            c = ComponentIR(**{**comp.__dict__})
            c.name = comp.name if i == 0 else f'{comp.name}_{i + 1}'
            c.optional = comp.optional or i >= lo
            c.count = None
            c.group, c.group_index = comp.name, i
            out.append(c)
        return out

    def _parse_location(self, cdata: dict, role: Role, pname: str, cname: str) -> LocationIR | None:
        if 'location' not in cdata:
            return None
        data = cdata['location']
        loc = loc_of(cdata, 'location')
        if not data:
            return None  # пустое ограничение = умолчание роли
        inside = role.is_inner
        try:
            lc = LocationConstraint.parse(data, context={'role': 'inner' if inside else 'outer'})
        except Exception as e:  # noqa: BLE001
            self.report.add('G006', f'некорректное `location: {data!r}` ({type(e).__name__}: {e})',
                            pattern=pname, component=cname, loc=loc,
                            hint='пример: `location: top, left` или `{top: 0, left: 0..1, right: 0..2}`')
            return None
        return LocationIR(
            padding={d.prop_name: r for d, r in lc.side_to_padding.items()},
            margin={d.prop_name: r for d, r in lc.side_to_margin.items()},
            raw=data,
        )

    # ------------------------------------------------------------------ массивы
    def _build_array(self, raw: dict, pname: str) -> ArrayIR:
        arr = ArrayIR()
        item = raw.get('item_pattern')
        arr.item_pattern = str(item) if item else None
        if not arr.item_pattern:
            self.report.add('G017', f'массив `{pname}` не задаёт `item_pattern`', pattern=pname, loc=loc_of(raw))

        direction = raw.get('direction')
        if direction is None:
            arr.direction = 'auto'
        elif str(direction) in ARRAY_DIRECTIONS:
            arr.direction = str(direction)
        else:
            self.report.add('G006', f'direction `{direction}` недопустим; допустимо {ARRAY_DIRECTIONS}',
                            pattern=pname, loc=loc_of(raw, 'direction'))

        count = self._range(raw, 'item_count', pname, open_range(1, None))
        inter = count.intersect(open_range(1, None)) if count else None
        if inter is None:
            self.report.add('G006', f'item_count `{count}` не допускает ни одного элемента', pattern=pname,
                            loc=loc_of(raw, 'item_count'))
            inter = open_range(1, None)
        arr.item_count = inter
        arr.gap = self._range(raw, 'gap', pname, open_range(0, 0))
        arr.distance_kind = str(raw.get('distance_kind', 'corner'))
        if arr.distance_kind not in DISTANCE_KINDS:
            self.report.add('G006', f'distance_kind `{arr.distance_kind}` недопустим; допустимо {DISTANCE_KINDS}',
                            pattern=pname, loc=loc_of(raw, 'distance_kind'))
            arr.distance_kind = 'corner'
        arr.allow_breakdown = bool(raw.get('allow_breakdown', False))
        arr.index_items = bool(raw.get('index_items', False))
        align = str(raw.get('align', 'both'))
        if align not in ARRAY_ALIGNS:
            self.report.add('G006', f'align `{align}` недопустим; допустимо {ARRAY_ALIGNS}', pattern=pname,
                            loc=loc_of(raw, 'align'))
            align = 'both'
        arr.align = align
        return arr

    # ------------------------------------------------------------------ отношения
    def _parse_relations(self, data: Any, pname: str, loc: SourceLoc) -> list[RelationIR]:
        if data is None:
            return []
        if not isinstance(data, list):
            self.report.add('G017', '`relations` должен быть списком', pattern=pname, loc=loc)
            return []
        out: list[RelationIR] = []
        for item in data:
            try:
                rel = self._parse_relation(item, loc)
            except ValueError as e:
                self.report.add('G006', f'некорректное отношение {item!r}: {e}', pattern=pname, loc=loc,
                                hint='примеры: `a.left == b.left`, `a.top >= b.bottom + 1`, `a.left - b.left in 0..2`')
                continue
            out.append(rel)
        return out

    @staticmethod
    def _norm_comp(name: str) -> str:
        return 'this' if name in _THIS_ALIASES else name

    def _parse_relation(self, item: Any, loc: SourceLoc) -> RelationIR:
        if isinstance(item, dict):
            a, b = str(item['a']), str(item['b'])
            delta = to_range(item.get('delta', 0))
            ma = re.fullmatch(r'(\w+)\.(left|right|top|bottom)', a)
            mb = re.fullmatch(r'(\w+)\.(left|right|top|bottom)', b)
            if not ma or not mb:
                raise ValueError('a и b должны иметь вид `компонент.сторона`')
            rel = RelationIR(EdgeRef(self._norm_comp(ma[1]), ma[2]), EdgeRef(self._norm_comp(mb[1]), mb[2]), delta,
                             text=str(item), loc=loc)
        else:
            text = str(item)
            m_in = _REL_IN.match(text)
            m_cmp = _REL_CMP.match(text)
            if m_in:
                rel = RelationIR(EdgeRef(self._norm_comp(m_in['a']), m_in['ae']),
                                 EdgeRef(self._norm_comp(m_in['b']), m_in['be']), to_range(m_in['r']), text=text,
                                 loc=loc)
            elif m_cmp:
                n = int(m_cmp['n'] or 0) * (-1 if m_cmp['sign'] == '-' else 1)
                op = m_cmp['op']
                delta = {
                    '==': open_range(n, n), '=': open_range(n, n),
                    '<=': open_range(None, n), '>=': open_range(n, None),
                    '<': open_range(None, n - 1), '>': open_range(n + 1, None),
                }[op]
                rel = RelationIR(EdgeRef(self._norm_comp(m_cmp['a']), m_cmp['ae']),
                                 EdgeRef(self._norm_comp(m_cmp['b']), m_cmp['be']), delta, text=text, loc=loc)
            else:
                raise ValueError('не удалось разобрать выражение')
        if axis_of(rel.a.edge) != axis_of(rel.b.edge):
            raise ValueError('стороны должны быть одной оси (left/right или top/bottom)')
        return rel


# --------------------------------------------------------------------------- публичный API

def load_grammar_ir(
        config_file: 'str | Path | None' = None,
        *,
        text: str | None = None,
        file_name: str = '<memory>',
        base_dir: 'str | Path | None' = None,
        cell_types_text: str | None = None,
) -> CompileResult:
    """Загрузить грамматику (файл или строку) и построить IR.

    Args:
        config_file: путь к файлу грамматики (`cnf/grammar_root.yml`).
        text: вместо файла можно передать YAML-текст.
        file_name: имя «файла» для диагностик при передаче `text`.
        base_dir: каталог для поиска импортируемых файлов (для `text`).
        cell_types_text: YAML-текст с ключом `cell_types` (дополняет/заменяет типы ячеек при загрузке из строки).
    """
    report = DiagnosticReport()
    fe = _Frontend(report)

    if text is not None:
        try:
            data = load_yaml_text(text, file_name)
        except Exception as e:  # noqa: BLE001
            report.add('G015', f'ошибка разбора YAML: {e}', loc=SourceLoc(file_name))
            return CompileResult(fe.ir, report)
        fe.ir.files.append(file_name)
        fe.process_document(data, file_name, Path(base_dir or '.'), True)
    elif config_file is not None:
        path = find_file_under_path(config_file, base_dir or '.') if not Path(config_file).exists() else Path(config_file)
        if path is None:
            report.add('G015', f'файл грамматики `{config_file}` не найден', loc=SourceLoc(str(config_file)))
            return CompileResult(fe.ir, report)
        fe.load_file(Path(path), True)
    else:
        raise ValueError('Specify `config_file` or `text`.')

    if cell_types_text:
        ct_data = load_yaml_text(cell_types_text, '<cell_types>')
        if isinstance(ct_data, dict) and 'cell_types' in ct_data:
            fe._load_cell_types(ct_data['cell_types'], '<cell_types>')

    fe.build_all()
    return CompileResult(fe.ir, report)
