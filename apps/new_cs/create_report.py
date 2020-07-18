import pandas as pd
import os
import re


path_main = os.getcwd() #+ r'\apps\new_cs'
path_src = os.path.join(path_main, 'src')


def create_new_CZK():
    _file_cs_1 = {
        'path': path_src + r'\Перечень ВСП в ЦС.xlsx',
        'sheet': 'Перечень ВСП в ЦС  ',
        'columns': {
            'D': 'urf_code',
            'F': 'gosb',
            'G': 'vsp',
            'J': 'fact_address',
            'K': 'ul_address',
            'M': 'tb_name',
            'N': 'subj_rf',
            'P': 'city',
            'R': 'format',
            'V': 'actions',
            'AH': 'kun',
        }
    }

    _file_nsi = {
        'path': path_src + r'\nsi.xlsx',
        'sheet': 0,
        'columns': {
            'A': 'vsp_code',
            'M': 'ul_address',
            'S': 'city',
            'T': 'street',
            'U': 'house',
            'V': 'address_add',
            'Y': 'near_vsp',
            'Z': 'near_vsp_dist',
            'CZ': 'subj_rf',
        }
    }

    data_cs = pd.read_excel(
        _file_cs_1['path'],
        sheet_name=_file_cs_1['sheet'],
        names=[_file_cs_1['columns'][col] for col in _file_cs_1['columns']],
        usecols=','.join(_file_cs_1['columns'].keys()),
    )
    data_cs['vsp_mod'] = data_cs['urf_code'].apply(
        lambda x:
            x[x.find('_')+1:x.rfind('_')].zfill(4) + '_' + x[x.rfind('_')+1:].zfill(5) if type(x) == str else ''
        )
    data_cs['gosb'] = data_cs['gosb'].fillna(0)
    data_cs['gosb'] = data_cs['gosb'].astype('int').astype('str').str.zfill(4)
    data_cs['gosb'] = data_cs.apply(lambda x: x['vsp_mod'][:4] if x['vsp_mod'] else x['gosb'], axis=1)
    data_cs['vsp'] = data_cs['vsp'].fillna(0)
    data_cs['vsp'] = data_cs['vsp'].astype('int').astype('str').str.zfill(5)
    data_cs['vsp_mod'] = data_cs.apply(
        lambda x:
            x['gosb'] + '_' + x['vsp']
            if not x['vsp_mod'] and x['vsp'] != '00000'
            else (x['gosb'] + '_новое' if not x['vsp_mod']
                  else x['vsp_mod']),
        axis=1
    )

    data_nsi = pd.read_excel(
        _file_nsi['path'],
        sheet_name=_file_nsi['sheet'],
        names=[_file_nsi['columns'][col] for col in _file_nsi['columns']],
        usecols=','.join(_file_nsi['columns'].keys()),
    )

    data_nsi['vsp_mod'] = data_nsi['vsp_code'].apply(
        lambda x:
            x[3:7].strip().zfill(4) + '_' + x[7:].strip().zfill(5) if type(x) == str else ''
    )

    data_nsi['near_vsp'] = data_nsi['near_vsp'].apply(
        lambda x:
            x[3:7].strip().zfill(4) + '_' + x[7:].strip().zfill(5) if type(x) == str else ''
    )

    data_nsi['house'] = data_nsi['house'].str.replace("'", '')
    data_nsi['fact_address'] = data_nsi.apply(
        lambda x: str(x['city']) + (
            ', ' + x['street'] if not pd.isnull(x['street']) else '') +
            (', ' + x['house'] if x['house'] != '' else ''),
        axis=1
    )

    gosb_list = pd.read_excel(path_src + r'\gosb_list.xlsx')

    data = data_cs.merge(
        data_nsi,
        on='vsp_mod',
        how='left',
        suffixes=['_cs', '_nsi']
    )

    gosb_list['gosb'] = gosb_list['gosb'].astype('int').astype('str').str.zfill(4)
    data = data.merge(
        gosb_list,
        on='gosb',
        how='left',
    )

    data['subj_rf'] = data.apply(lambda x: x['subj_rf_nsi'] if not pd.isnull(x['subj_rf_nsi']) else x['subj_rf_cs'], axis=1)
    data['city'] = data.apply(lambda x: x['city_nsi'] if not pd.isnull(x['city_nsi']) else x['city_cs'], axis=1)
    data['ul_address'] = data.apply(lambda x: x['ul_address_nsi'] if not pd.isnull(x['ul_address_nsi']) else x['ul_address_cs'], axis=1)
    data['fact_address'] = data.apply(lambda x: x['fact_address_nsi'] if not pd.isnull(x['fact_address_nsi']) else x['fact_address_cs'], axis=1)

    def dt_from_kun(x):
        if type(x) == str:
            dt = re.findall(r'\d{1,2}\.\d{1,2}\.\d{2,4}', x)
            if len(dt) > 0:
                return dt[-1]
        return ''

    data['dt_kun'] = data['kun'].apply(dt_from_kun)

    city_pattern = re.compile(
        r'^г[\. ]{0,2}|^д[\. ]{0,2}|^с[\. ]{0,2}|^пгт[\. ]{0,2}|^п[\. ]{0,2}|^м[\. ]{0,2}|^р\.п[\. ]{0,2}|^х[\. ]{0,2}|'
    )

    data.fillna('', inplace=True)

    def check_adr(x):
        adr = str(x['ul_address']).lower()
        city = str(x['city']).lower()
        house = str(x['house']).lower()

        if not adr or not city:
            return 'Совпадает'
        city = city_pattern.sub('', city)
        if city not in adr:
            return 'Не совпадает'
        if house:
            house = re.sub(r'\D', '', house)
            if house in adr[7:]:
                return 'Совпадает'
            else:
                return 'Не совпадает'

        return 'Совпадает'

    data['adr_equal'] = data.apply(check_adr, axis=1)

    data['plan_dt_open'] = ''
    data['plan_dt_close'] = ''
    data['dt_close'] = ''

    cols = [
        'tb_name',
        'gosb_name',
        'vsp_mod',
        'subj_rf',
        'city',
        'street',
        'house',
        'address_add',
        'ul_address',
        'adr_equal',
        'format',
        'actions',
        'plan_dt_open',
        'plan_dt_close',
        'dt_close',
        'kun',
        'dt_kun',
        'fact_address',
    ]

    data[cols].to_excel(r'D:\projects\portal_apps\apps\new_cs\cs_final.xlsx')


if __name__ == '__main__':
    create_new_CZK()
