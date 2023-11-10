# test_classify_cells.py

from src.confidence_matching import read_cell_types


def run_matching(tokens, only=()):
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


def run_classification(tokens, show_bad_only=False):
    cell_types = read_cell_types()
    for t in tokens:
        # Очищаем токен от пробелов и лишних кавычек по краям
        t = t.strip().strip('"\'')
        matched = []
        for name, ct in cell_types.items():
            m = ct.match(t)
            if m:
                confidence = round(m.confidence * 100)
                # text = m.re_match.group(0)
                text = m.cell_text
                matched.append((confidence, f"`{ct.name}` \t-> [0]: `{text}`"))

        if not matched:
            print("Nothing matched!")
            continue

        matched.sort(key=lambda c_t: (-c_t[0], t))
        confident = matched[0][0] >= 50
        if not confident:
            print("Recognized with confidence of < 50% !")
        elif show_bad_only:
            continue

        print()
        print(f' ::::::: `{t}` ::::::: ')
        print(' ' * 9, '-' * len(t), ' ' * 9)

        for confidence, ct in matched:
            if confident and confidence < 50:
                break
            print(f'{confidence}: {ct}')


def test_content_from_real_sheets():
    filepaths = [
        r'../materials/ОН_ФАТ_1_курс - unique-values.txt',
        r'../materials/ОН_ФЭВТ_1 курс - unique-values.txt',
        r'../materials/ОН_ФЭВТ_3 курс - unique-values.txt',
        r'../materials/ОН_Магистратура_2 курс ХТФ - unique-values.txt',
        r'../materials/ОН_Магистратура_ 1 курс ФТКМ - unique-values.txt',
        r'../materials/groupnames.txt',
    ]

    values = set()
    for filepath in filepaths:
        with open(filepath, encoding='utf8') as f:
            text = f.read()
        values |= set(filter(None, text.split('\n')))
        del text

    # run_matching(sorted(values), only=(
    #     # 'month_name',
    #     # 'week_day',
    #     # 'fake_month_day',
    #     # 'month_day',
    #     # 'discipline',
    #     # 'room',
    #     # 'teacher'
    #     # 'group',
    #     # 'hour_range'
    #     'explicit_dates'
    #     # 'explicit_hours'
    # ))
    run_classification(sorted(values), True)


if __name__ == '__main__':
    test_content_from_real_sheets()