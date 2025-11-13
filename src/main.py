# entry point & experiments

from export.vstu import xls_to_json

if __name__ == '__main__':
    print('Hi!')
    xls_to_json('../tests/test_data/ОН_Магистратура_1 курс ФЭВТ 2025.xlsx')
    print('Bye.')
