# excel.py

"""
Пред-обработка Excel-таблиц и вспомогательные операции над ними.
"""


from openpyxl import load_workbook


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


if __name__ == '__main__':
    paths = (
        r'c:\User\Downloads\ОН_Магистратура_2 курс ХТФ.xlsx',
    )
    for filename in paths:
        extract_unique_values_to_txt(filename)
