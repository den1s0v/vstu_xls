# test_classify_cells.py

from src.confidence_matching import read_cell_types


def run_classification(tokens, only=('discipline', '!! room', '!! teacher')):
    cell_types = read_cell_types()
    for name, ct in cell_types.items():
        ###
        if only and name not in only:
            continue
        ###

        print()
        print(f' ::::::: {name} ::::::: ')
        print()
        matched = []
        for t in tokens:
            # Очищаем токен от пробелов и лишних кавычек по краям
            t = t.strip().strip('"\'')

            m = ct.match(t)
            if m:
                confidence = round(m.pattern.confidence * 100)
                matched.append((confidence, f"`{t}` \t-> [0]: `{m.re_match.group(0)}`"))

        matched.sort(key=lambda c_t: (-c_t[0], t.lower()))
        for confidence, t in matched:
            print(f'{ct.name}: {confidence}\t{t}')


if __name__ == '__main__':
    filepaths = [
        r'../materials/ОН_ФЭВТ_1 курс - unique-values.txt',
        r'../materials/ОН_ФЭВТ_3 курс - unique-values.txt',
    ]

    values = set()
    for filepath in filepaths:
        with open(filepath) as f:
            text = f.read()
        values |= set(filter(None, text.split('\n')))
        del text

    run_classification(sorted(values))
