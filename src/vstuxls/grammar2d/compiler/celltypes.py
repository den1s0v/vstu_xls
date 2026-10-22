"""Лексический анализ типов ячеек (аналог проверки конфликтов в lex).

Тип ячейки — набор регулярных выражений с уверенностью. Два типа *конфликтуют*, если существует строка,
которую уверенно (выше порога терминалов) распознают оба. Конфликт не обязательно ошибка — его снимает структура
грамматики, — но он должен быть разрешён явно: `priority` / `except` у типа (вместо ручных lookahead в регулярках).

Метод: из каждого регулярного выражения порождаются строки-кандидаты (обход дерева `re._parser`), каждая
проверяется реальным матчером (`StringPattern.match`). Найденный пример — *свидетель* пересечения, он достоверен.
Отсутствие примера не доказывает непересечение (выборка), поэтому отчёты — предупреждения.

Диагностики: LEX001 (общий свидетель двух типов), LEX002 (анализ ограничен), LEX003 (паттерн недостижим:
перекрыт более уверенным паттерном того же типа), LEX004 (некорректное выражение), LEX005 (пример не распознаётся).
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

try:  # Python >= 3.11
    from re import _constants as _sre_const
    from re import _parser as _sre_parse
except ImportError:  # pragma: no cover
    import sre_constants as _sre_const  # type: ignore
    import sre_parse as _sre_parse  # type: ignore

from vstuxls.grammar2d.compiler.diagnostics import DiagnosticReport, Severity
from vstuxls.grammar2d.compiler.ir import CellTypeIR, GrammarIR, PKind

# Символы для «любого символа» и отрицаний классов: разные категории, чтобы поймать больше пересечений.
_POOL = list('абвгдеёжзийклмнопрстуфхцчшщыэюя' 'АБВГДЕЁЖЗИКЛМНОПРСТУФХЦЧШЩЭЮЯ' 'abcxyzABCXYZ' '0123456789' '  -.,()/')
_DIGITS = '0123456789'
_SPACES = ' '
_WORD = 'абвгдеАБВГДЕabcABC0123_'


@dataclass
class CompiledPattern:
    ir_data: dict
    confidence: float
    regex: object  # StringPattern
    source: str


@dataclass
class CompiledType:
    ir: CellTypeIR
    patterns: list[CompiledPattern] = field(default_factory=list)

    def first_match(self, text: str) -> CompiledPattern | None:
        """Как `CellType.match`: паттерны по убыванию уверенности, берётся первый совпавший."""
        for cp in self.patterns:
            try:
                if cp.regex.match(text):
                    return cp
            except Exception:  # noqa: BLE001 — защитно: сбои препроцессоров не должны ронять анализ
                continue
        return None


# --------------------------------------------------------------------------- генерация строк

class _Gen:
    def __init__(self, rng: random.Random, ignore_case: bool = False) -> None:
        self.rng = rng
        self.ignore_case = ignore_case
        self.limited = False  # встретились конструкции, которые не умеем порождать

    def gen(self, parsed, max_rep: int = 3) -> str:
        out: list[str] = []
        for op, av in parsed:
            out.append(self._one(op, av, max_rep))
        return ''.join(out)

    def _one(self, op, av, max_rep: int) -> str:
        C = _sre_const
        rng = self.rng
        if op is C.LITERAL:
            ch = chr(av)
            return ch.swapcase() if self.ignore_case and rng.random() < 0.3 else ch
        if op is C.NOT_LITERAL:
            return rng.choice([c for c in _POOL if ord(c) != av])
        if op is C.ANY:
            return rng.choice([c for c in _POOL if c != '\n'])
        if op is C.IN:
            return self._in(av)
        if op is C.BRANCH:
            return self.gen(rng.choice(av[1]), max_rep)
        if op is C.SUBPATTERN:
            return self.gen(av[-1], max_rep)
        if op in (C.MAX_REPEAT, C.MIN_REPEAT) or getattr(C, 'POSSESSIVE_REPEAT', None) is op:
            lo, hi, sub = av
            hi_eff = min(hi, lo + max_rep) if hi != _sre_const.MAXREPEAT else lo + max_rep
            n = rng.randint(lo, max(lo, hi_eff))
            return ''.join(self.gen(sub, max_rep) for _ in range(n))
        if getattr(C, 'ATOMIC_GROUP', None) is op:
            return self.gen(av, max_rep)
        if op in (C.AT, C.ASSERT, C.ASSERT_NOT):
            # Якоря и условия просмотра не порождают символов; корректность проверит реальный матчер.
            return ''
        if op is C.GROUPREF:
            self.limited = True
            return ''
        self.limited = True
        return ''

    def _in(self, items) -> str:
        C = _sre_const
        negate = False
        chars: list[str] = []
        for op, av in items:
            if op is C.NEGATE:
                negate = True
            elif op is C.LITERAL:
                chars.append(chr(av))
            elif op is C.RANGE:
                lo, hi = av
                span = list(range(lo, min(hi, lo + 80) + 1))
                chars.extend(chr(c) for c in self.rng.sample(span, min(len(span), 6)))
            elif op is C.CATEGORY:
                chars.extend(self._category(av))
        if negate:
            banned = set(chars)
            cands = [c for c in _POOL if c not in banned and c != '\n']
            return self.rng.choice(cands) if cands else ' '
        if not chars:
            self.limited = True
            return ''
        c = self.rng.choice(chars)
        return c.swapcase() if self.ignore_case and self.rng.random() < 0.3 else c

    def _category(self, cat) -> list[str]:
        C = _sre_const
        name = str(cat)
        if 'NOT_DIGIT' in name:
            return [c for c in _POOL if c not in _DIGITS]
        if 'DIGIT' in name:
            return list(_DIGITS)
        if 'NOT_SPACE' in name:
            return [c for c in _POOL if c not in _SPACES]
        if 'SPACE' in name:
            return list(_SPACES)
        if 'NOT_WORD' in name:
            return [' ', '-', '.', ',']
        if 'WORD' in name:
            return list(_WORD)
        return list(_POOL)


def sample_strings(pattern_source: str, flags: int, n: int, rng: random.Random) -> tuple[list[str], bool]:
    """Порождает до `n` различных строк, которые *могут* подойти под регулярное выражение."""
    try:
        parsed = _sre_parse.parse(pattern_source, flags)
    except Exception:  # noqa: BLE001
        return [], True
    gen = _Gen(rng, ignore_case=bool(flags & re.IGNORECASE))
    seen: dict[str, None] = {}
    attempts = 0
    while len(seen) < n and attempts < n * 6:
        attempts += 1
        s = gen.gen(parsed, max_rep=1 + attempts % 4)
        seen.setdefault(s, None)
    return list(seen), gen.limited


# --------------------------------------------------------------------------- анализ

def _compile_types(ir: GrammarIR, report: DiagnosticReport) -> dict[str, CompiledType]:
    from vstuxls.string_matching import StringPattern  # импорт регистрирует трансформеры строк

    result: dict[str, CompiledType] = {}
    for name, ct in ir.cell_types.items():
        comp = CompiledType(ct)
        for sp in ct.patterns:
            data = dict(sp.data)
            try:
                regex = StringPattern(data, content_class=name)
            except AssertionError as e:
                report.add('LEX004', f'тип `{name}`: {e}', loc=sp.loc)
                continue
            except Exception as e:  # noqa: BLE001 — re.error, KeyError, ValueError...
                report.add('LEX004', f'тип `{name}`: паттерн {data.get("pattern")!r} не компилируется: {e}',
                           loc=sp.loc)
                continue
            comp.patterns.append(CompiledPattern(data, float(regex.confidence), regex, str(regex.pattern)))
        comp.patterns.sort(key=lambda c: -c.confidence)
        result[name] = comp
    return result


def _used_thresholds(ir: GrammarIR) -> dict[str, float]:
    """Для каждого используемого типа — минимальный порог точности среди терминалов, которые его применяют."""
    thr: dict[str, float] = {}
    for p in ir:
        if p.kind is PKind.CELL and p.content_type:
            t = p.policy.effective_threshold()
            thr[p.content_type] = min(thr.get(p.content_type, 1.0), t)
    return thr


def _resolved(a: CellTypeIR, b: CellTypeIR) -> bool:
    return a.priority != b.priority or b.name in a.except_types or a.name in b.except_types


def analyze_cell_types(ir: GrammarIR, report: DiagnosticReport, *, samples: int = 40, seed: int = 0) -> None:
    if not ir.cell_types:
        return
    types = _compile_types(ir, report)
    thresholds = _used_thresholds(ir)
    rng = random.Random(seed)

    # --- примеры из описания типа должны распознаваться
    for name, comp in types.items():
        for ex in comp.ir.examples:
            if comp.first_match(ex) is None:
                report.add('LEX005', f'пример {ex!r} не распознаётся типом `{name}`', loc=comp.ir.loc)

    # --- кандидаты-строки и пересечения
    overlaps: dict[tuple[str, str], tuple[str, float, float]] = {}
    for a_name, a in types.items():
        if a_name not in thresholds:
            continue  # тип не используется терминалами (см. G007): конфликтовать не с чем
        ta = thresholds[a_name]
        for idx, cp in enumerate(a.patterns):
            strings, limited = sample_strings(cp.source, _flags_of(cp), samples, rng)
            strings = _embed(strings, getattr(cp.regex, 'anchors', ('start',)), rng)
            own = [s for s in strings if a.first_match(s) is not None]
            if not own:
                report.add('LEX002', f'тип `{a_name}`: не удалось породить строки для анализа паттерна '
                                     f'{cp.ir_data.get("pattern")!r}', loc=_loc_of(a, cp))
                continue
            _check_shadowed(report, a_name, a, idx, cp, strings)
            if cp.confidence < ta:
                continue  # паттерн ниже порога терминалов: не влияет на разбор
            for s in own:
                ma = a.first_match(s)
                if ma is None or ma.confidence < ta:
                    continue
                for b_name, b in types.items():
                    if b_name == a_name or b_name not in thresholds:
                        continue
                    mb = b.first_match(s)
                    if mb is None or mb.confidence < thresholds[b_name]:
                        continue
                    key = tuple(sorted((a_name, b_name)))
                    cur = overlaps.get(key)
                    score = min(ma.confidence, mb.confidence)
                    if cur is None or score > min(cur[1], cur[2]):
                        if key[0] == a_name:
                            overlaps[key] = (s, ma.confidence, mb.confidence)
                        else:
                            overlaps[key] = (s, mb.confidence, ma.confidence)

    ir.lexical_conflicts = {frozenset(k) for k in overlaps}
    # Один отчёт на тип-«владелец» (первый в файле): список типов, с которыми есть общие строки.
    order = {n: i for i, n in enumerate(ir.cell_types)}
    by_owner: dict[str, list[tuple[str, str, float, float]]] = {}
    for (n1, n2), (s, c1, c2) in overlaps.items():
        if _resolved(types[n1].ir, types[n2].ir):
            continue
        owner, other = sorted((n1, n2), key=order.get)
        ca, cb = (c1, c2) if owner == n1 else (c2, c1)
        by_owner.setdefault(owner, []).append((other, s, ca, cb))
    for owner in sorted(by_owner, key=order.get):
        items = sorted(by_owner[owner], key=lambda t: -min(t[2], t[3]))
        strongest = min(items[0][2], items[0][3])
        sev = Severity.WARNING if strongest >= 0.9 else Severity.INFO
        other, s, ca, cb = items[0]
        report.add(
            'LEX001',
            f'тип `{owner}` делит строки с типами: ' + ', '.join(f'`{t[0]}`' for t in items),
            severity=sev, loc=types[owner].ir.loc,
            witness=f'{s!r} -> {owner}: {ca:.2f}, {other}: {cb:.2f}',
            related=[f'`{o}`: {s2!r} ({owner}: {a_:.2f}, {o}: {b_:.2f})' for o, s2, a_, b_ in items[1:6]],
            hint='если различать типы нужно уже на уровне ячейки, задайте `priority` (больше — вытесняет) '
                 'или `except: [тип]` вместо ручного lookahead в регулярном выражении; '
                 'если конфликт снимает структура грамматики, оставьте как есть',
        )


_SUFFIXES = (' х', ', Ф.', ' 12', ' Аб')
_PREFIXES = ('Х ', '1 ', 'аб ', ', ')


def _embed(strings: list[str], anchors: tuple, rng: random.Random) -> list[str]:
    """Для паттернов без якоря конца/начала добавляет варианты с «хвостом»/«головой»:
    именно на них паттерн отличается от более строгих (полное совпадение)."""
    out = list(strings)
    free_end = 'end' not in anchors
    free_start = 'start' not in anchors
    for s in strings[: max(1, len(strings) // 2)]:
        if free_end:
            out.append(s + rng.choice(_SUFFIXES))
        if free_start:
            out.append(rng.choice(_PREFIXES) + s)
    return list(dict.fromkeys(out))


def _flags_of(cp: CompiledPattern) -> int:
    f = getattr(cp.regex, 'pattern_flags', 0)
    return int(f) if isinstance(f, int) else 0


def _loc_of(ct: CompiledType, cp: CompiledPattern):
    for sp in ct.ir.patterns:
        if sp.data is cp.ir_data or sp.data.get('pattern') == cp.ir_data.get('pattern'):
            return sp.loc
    return ct.ir.loc


def _check_shadowed(report: DiagnosticReport, name: str, a: CompiledType, idx: int, cp: CompiledPattern,
                    strings: list[str]) -> None:
    """LEX003: паттерн недостижим, если любая порождённая им строка уже совпала с более уверенным паттерном."""
    if idx == 0 or len(strings) < 8:
        return
    valid = [s for s in strings if _matches(cp, s)]
    if len(valid) < 8:
        return
    higher = a.patterns[:idx]
    higher = [h for h in higher if h.confidence >= cp.confidence]
    if not higher:
        return
    for s in valid:
        if not any(_matches(h, s) for h in higher):
            return
    report.add('LEX003', f'тип `{name}`: паттерн {cp.ir_data.get("pattern")!r} (уверенность {cp.confidence}) '
                         f'не достижим: все {len(valid)} порождённых им строк уже распознаются более уверенным',
               loc=_loc_of(a, cp), hint='анализ по выборке; удалите паттерн или сузьте вышестоящий')


def _matches(cp: CompiledPattern, s: str) -> bool:
    try:
        return bool(cp.regex.match(s))
    except Exception:  # noqa: BLE001
        return False
