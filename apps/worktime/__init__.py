import pandas as pd
import os


from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from win32com.client import Dispatch
from zipfile import ZipFile

from db.db_admin import decorator_update_row


# ВОТ ЗДЕСЬ МЕНЯТЬ ПЕРИОД
dt_start = '2020-06-24'
dt_end = '2020-06-24'
# =======================

main_path = os.getcwd()
main_path = r'C:\work\portal_apps\apps\worktime'
src_path = os.path.join(main_path, 'src')
data_path = os.path.join(src_path, 'data.csv')
data_path2 = os.path.join(src_path, 'data.xlsx')
nsi_path = os.path.join(src_path, 'nsi.csv')
# template_path = os.path.join(src_path, 'Шаблон.xlsx')
template_path = r'\\Braga101\Vol2\SUDR_PCP_BR\For_Site_2\src\Шаблон.xlsx'
out_path = os.path.join(main_path, 'out')
sql_path = os.path.join(main_path, 'worktime.sql')
zip_path = os.path.join(out_path, 'worktime.zip')
str_conn = 'DSN=TDSB14;pwd=Gjdtpkj19'


tb_list = {
    'Волго-Вятский банк': 'vvb',
    'Юго-Западный банк': 'uzb',
    'Уральский банк': 'urb',
    'Северо-Западный банк': 'szb',
    'Среднерусский банк': 'srb',
    'Сибирский банк': 'sib',
    'Поволжский банк': 'pvb',
    'Московский банк': 'mb',
    'Дальневосточный банк': 'dvb',
    'Центрально-Черноземный банк': 'ccb',
    'Байкальский банк': 'bb',
}

month_list = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля']


def save_df_to_excel(df, file_pattern, new_name, sheet='ВСП', first_row=1, first_column=1, save_pdf=True, **kwargs):
    xl = Dispatch("Excel.Application")
    wb = xl.Workbooks.Open(file_pattern)
    xl.Application.Calculation = -4135
    xl.Application.ScreenUpdating = False
    xl.Application.DisplayAlerts = False
    ws = wb.Sheets(sheet)

    if kwargs.get('header_str'):
        ws.cells(1, 1).value = kwargs['header_str']

    if 'FA_METRO' in df.columns:
        ws.Columns(11).EntireColumn.Hidden = False

    rng = ws.Range(
        ws.Cells(first_row, first_column),
        ws.Cells(first_row + len(df) - 1, first_column + len(df.columns) - 1)
    )

    rng.Value = tuple(
        [tuple([str(y) for y in x]) for x in df.values]
    )

    xl.Application.Calculation = -4105
    xl.Application.ScreenUpdating = True

    # костыль для сохранения в pdf
    if save_pdf:
         ws.PageSetup.Orientation = 2
         wb.ActiveSheet.ExportAsFixedFormat(0, new_name[:-5] + '.pdf')
         ws.PageSetup.Orientation = 1

    wb.SaveAs(new_name)
    xl.Application.DisplayAlerts = True
    wb.Close()
    xl.Quit()


def get_data():
    nsi = pd.read_csv(nsi_path, sep=';', encoding='cp1251')

    data = pd.read_excel(data_path2)
    data = data[~pd.isnull(data['work_time'])]
    data['vsp_mod'] = data['vsp_name'].apply(lambda x: x[4:x.rfind('_')].zfill(4) + '_' + x[x.rfind('_') + 1:].zfill(5))

    data = data.merge(
        nsi,
        on='vsp_mod',
        how='left',
    )

    return data


@decorator_update_row
def worktime_reports_for_site(with_vip=True, with_ul=True, use_db=True, dt_start='', dt_end='', data_only=False, save_pdf=False):
    # if use_db:
    #     try:
    #         from z_dbworker import Tera
    #         with open(sql_path, 'r') as f:
    #             sql = f.read()
    #         tera = Tera(str_conn)
    #         data = tera.get_data(sql.format(dt_start, dt_end))
    #         tera.close()
    #         data.to_csv(data_path, sep=';', encoding='cp1251')
    #     except Exception as err:
    #         print(err)
    #         return 0

    # zipObj = ZipFile(zip_path, 'w')
    # if data_only:
    #     zipObj.write(data_path)
    #     zipObj.close()
    #     return 0

    data = pd.read_csv(data_path, sep=';', encoding='cp1251')
    data = data.sort_values(['gosb', 'vsp', 'dt'])
    data['gosb'] = data['gosb'].astype('int')
    data['vsp'] = data['vsp'].astype('int')
    data['dt'] = data['dt'].astype('str')

    max_dt, min_dt = data['dt'].max(), data['dt'].min()
    if max_dt == min_dt:
        header_str = '{} {} 2020г. -  НЕРАБОЧИЙ ДЕНЬ ДЛЯ ВСЕХ ВСП, КРОМЕ ДЕЖУРНЫХ ВСП.\n(см. в таблице ниже)'.format(
            min_dt[8:], month_list[int(min_dt[5:7]) - 1]
        )
    else:
        header_str = 'С {} {} 2020г. по {} {} 2020г. -  НЕРАБОЧИЙ ДЕНЬ ДЛЯ ВСЕХ ВСП, КРОМЕ ДЕЖУРНЫХ ВСП.\n(см. в таблице ниже)'.format(
            min_dt[8:], month_list[int(min_dt[5:7]) - 1], max_dt[8:], month_list[int(max_dt[5:7]) - 1]
        )

    data['dt'] = data['dt'].str[8:] + '.' + data['dt'].str[5:7] + '.' + data['dt'].str[:4]

    cols = ['level_0', 'gosb', 'vsp', 'category_serv', 'subj_RF', 'city', 'address', 'dt', 'worktime', 'dinner_time']

    if not with_vip:
        data = data[data['vip'] != 1]

    if not with_ul:
        data = data[data['category_serv'] != 'обслуживание юридических лиц']

    # str_for_name = 'vsp_' + dt_start[8:] + dt_start[5:7] + '-' + dt_end[8:] + dt_end[5:7] + '_'
    str_for_name = 'vsp_3003-0504_'
    for tb in tb_list.keys():
        print(tb)
        tb_data = data[data['tb'] == tb].reset_index().reset_index()
        tb_data['level_0'] = tb_data['level_0'] + 1

        # костыль для МБ
        if tb == 'Московский банк':
            tb_data = tb_data[cols + ['FA_METRO']]
        else:
            tb_data = tb_data[cols]
        save_df_to_excel(tb_data,
                           template_path, out_path + '\\' + str_for_name + tb_list[tb] + '.xlsx',
                           sheet='ВСП',
                           first_row=3,
                           header_str=header_str,
                           )
        # zipObj.write(out_path + '\\' + str_for_name + tb_list[tb] + '.xlsx')
        # zipObj.write(out_path + '\\' + str_for_name + tb_list[tb] + '.pdf')
    # zipObj.close()



if __name__ == '__main__':
    worktime_reports_for_site(with_vip=False, with_ul=False, use_db=True, dt_start=dt_start, dt_end=dt_end, data_only=False)