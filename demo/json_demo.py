# entry point & experiments

from vstuxls.export.vstu import xls_to_json

if __name__ == '__main__':
    print('Hi!')
    # xls_to_json('../tests/test_data/ОН_ФЭУ_3 курс_v2.xlsx')
    xls_to_json('../tests/test_data/ОН_ФЭВТ_4 курс 2023.xlsx')
    print('Bye.')
