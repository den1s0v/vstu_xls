# entry point & experiments

from export.vstu import xls_to_json

if __name__ == '__main__':
    print('Hi!')
    xls_to_json('../tests/test_data/ОН_ФЭУ_3 курс_v2.xlsx')
    print('Bye.')
