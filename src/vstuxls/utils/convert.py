# convert.py

"""
Преобразовать файл старого формата Excel 2003 (.xls)  В новый формат Excel 2007 (.xlsx)
Двумя способами:
 - посредством установленного на компьютер Excel, который запускается посредством COM-объекта
 - (если предыдущий вариант недоступен) при помощи библиотеки [xls2xlsx](https://pypi.org/project/xls2xlsx/)
"""
from pathlib import Path

from xls2xlsx import XLS2XLSX

from . import Checkpointer

MS_EXCEL_AVAILABLE = False  # True: yes, False: no, None: not checked yet.

try:
    import win32com.client as win32
except ImportError:
    print(':WARN: pywin32 is not installed, using xls2xlsx')
    MS_EXCEL_AVAILABLE = False


def convert_xls_to_xlsx(filename_in, filename_out=None) -> str | None:
    """ Convert xls file to xlsx using either MS Excel if possible otherwise xls2xlsx as fallback
    (xls2xlsx is usually slower and may change content a little but is environment-independent).
    """
    if MS_EXCEL_AVAILABLE is not False:
        saved_as = run_excel(filename_in, filename_out)
        if saved_as:
            return saved_as
    return run_xls2xlsx(filename_in, filename_out)


def run_excel(filename_in, filename_out=None) -> str | None:
    global MS_EXCEL_AVAILABLE
    # print(filename_in)
    print('Running MS Excel ...')
    ch = Checkpointer()
    try:
        excel = win32.gencache.EnsureDispatch('Excel.Application') # type: ignore
        ch.hit('Excel invoked')
        wb = excel.Workbooks.Open(filename_in)
        ch.hit('workbook opened')
        filename_out = filename_out or filename_in + "x"
        ch.hit('workbook opened')
        # print(filename_out)
        # FileFormat = 51 is for .xlsx extension
        wb.SaveAs(filename_out, FileFormat=51)
        ch.hit('xlsx saved')
        wb.Close()
        excel.Application.Quit()
        ch.hit('Excel closed')
        MS_EXCEL_AVAILABLE = True
    except Exception as e:  # todo: check out specific exception classes
        MS_EXCEL_AVAILABLE = False
        print(f'Exception in {__name__}.run_Excel() with args: {(filename_in, filename_out)} :')
        print(f'{type(e)}: {e!s}')
        return None
    return filename_out


def run_xls2xlsx(filename_in, filename_out=None) -> str | None:
    print('Running xls2xlsx ...')
    try:
        ch = Checkpointer()
        x2x = XLS2XLSX(filename_in)
        ch.hit('xls2xlsx task created')
        if not filename_out:
            filename_out = filename_in + "x"
        x2x.to_xlsx(filename_out)
        ch.hit('xlsx saved')
        ch.since_start('conversion took')
    except Exception as e:  # todo: check out specific exception classes
        print(f'Exception in {__name__}.run_xls2xlsx() with args: {(filename_in, filename_out)} :')
        print(f'{type(e)}: {e!s}')
        return None
    return filename_out


def convert_many(paths: list[str | Path]):
    ch = Checkpointer()

    for filename in paths:
        convert_xls_to_xlsx(str(filename))

    ch.hit(f'COMPLETE! files converted: {len(paths)}')


def convert_all_in_dir(folder_path: str | Path = '.') -> None:
    """Найти все `.xls` и сконвертировать только те, у которых рядом нет `.xlsx`."""
    root = Path(folder_path)
    xls_paths = list(root.rglob('*.xls'))

    to_convert: list[Path] = []
    for xls_path in xls_paths:
        xlsx_candidate = xls_path.with_suffix('.xlsx')
        if xlsx_candidate.exists():
            # Уже есть сконвертированный файл — пропускаем
            print(f'SKIP (xlsx exists): {xls_path} -> {xlsx_candidate}')
            continue
        to_convert.append(xls_path)

    if not to_convert:
        print(f'No .xls files to convert in {root} (all have .xlsx siblings).')
        return

    convert_many(to_convert)
