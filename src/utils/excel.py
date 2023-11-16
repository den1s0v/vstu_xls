# excel.py

"""
Пред-обработка Excel-таблиц и вспомогательные операции над ними.
"""


from openpyxl import load_workbook
from openpyxl.comments import Comment
from openpyxl.styles import PatternFill

from confidence_matching import CellClassifier


def unique_values_of_whole_sheet(sheet) -> list[str]:
    values = {str(v).strip() for row in sheet.values for v in row if v is not None}  # and v.strip()
    return sorted(values)


def extract_unique_values_to_txt(filename_xlsx_in, filename_txt_out=None):
    wb = load_workbook(filename=filename_xlsx_in, read_only=True)
    sh = wb.active
    values = unique_values_of_whole_sheet(sh)
    filename_out = filename_txt_out or filename_xlsx_in.replace('.xlsx', ' - unique-values.txt')
    with open(filename_out, 'w') as f:
        f.write('\n'.join(values) + '\n')


classifier = None

def classify_cell_content(content: str) -> ('best class: str', 'best confidence: float', 'matches: list[Match]'):
    global classifier
    classifier = classifier or CellClassifier()
    matches = classifier.match(content)
    if not matches:
        return ['Unknown', 0.0, []]
    best = matches[0]
    return [best.pattern.content_class.name, best.confidence, matches]


def colorize_values_on_sheet(sheet) -> None:
    for row in sheet.iter_rows():
        for cell in row:
            content = str(cell.value).strip()
            if content and content != 'None':
                class_name, confidence, _ = classify_cell_content(content)
                comment = f'{class_name}: {round(confidence * 100)}' or 'Не определено'
                if confidence <= 0.5:
                    color = 'FF0000'
                elif confidence >= 0.85:
                    color = '00FF00'
                else:
                    color = 'FFCC00'  # thick yellow

                cell.fill = PatternFill("solid", fgColor=color)
                comment = Comment(text=comment, author='Cell classifier')
                # Assign the comment to the cell.
                try:
                    cell.comment = comment
                except AttributeError:
                    # print('failed to add a comment to cell', cell.coordinate)
                    pass


def mark_recognized_values_in_sheet(filename_xlsx_in, filename_txt_out=None):
    wb = load_workbook(filename=filename_xlsx_in)
    sh = wb.active
    # update content
    colorize_values_on_sheet(sh)
    # save back
    filename_out = filename_txt_out or filename_xlsx_in.replace('.xlsx', ' - cells-annotated.xlsx')
    wb.save(filename_out)
    print('Saved file with cells annotated as', filename_out)


def main():
    paths = (
        r'c:\Users\Student\Downloads\ОН_ФТПП_3 курс.xlsx',
    )
    for filename in paths:
        # extract_unique_values_to_txt(filename)
        mark_recognized_values_in_sheet(filename)


if __name__ == '__main__':
    main()
