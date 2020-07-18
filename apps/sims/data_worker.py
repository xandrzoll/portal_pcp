import pandas as pd
import re
import sqlite3
import pyodbc


SQL_DATABASE = 'C:\work\Portal\db\database.db'
TERA_STR_CONN = 'DSN=TDSB14'


def load_delivery(delivery_type=0, path_to_file='', sh='Sheet1', save_db=True):
    delivery = pd.read_excel(path_to_file, sh)
    if delivery_type == 0:
        # 0 - автопополнение
        delivery = delivery[['Дата поставки', 'ВСП', 'Кол-во доставл', 'ID Обращения', 'ID Организации ВК', 'Статус']]
        delivery.columns = ['dt', 'vsp', 'delivery_cnt', 'id', 'dep_id', 'status']
        delivery['vsp'] = delivery['vsp'].apply(
            lambda x:
            x[:x.rfind('/')].zfill(4) + '_' + x[x.rfind('/') + 1:].zfill(5)
            if type(x) == str and '/' in x
            else x
        )
        delivery['vsp'] = delivery['vsp'].apply(lambda x: '8647' + x[4:] if x[:4] == '0029' else x)

        delivery['delivery_cnt'] = delivery['delivery_cnt'].apply(lambda x: x if x >= 40 else x * 100)
        # delivery = delivery[delivery['delivery_cnt'] > 0]
        delivery.loc[delivery['dt'] == '-', 'dt'] = None
        delivery['dt'] = delivery['dt'].astype('datetime64[ns]', errors='ignore')

        delivery['delivery_type'] = 0
        delivery.loc[
            (
                delivery['delivery_cnt'] > 0
            ),
            'is_delivered'] = 1

    # ========================================================================
    if delivery_type == 1:
        # 1 - срочный заказ
        delivery.loc[
            (
                (delivery['Состояние'] == 'Завершено')
                | (delivery['Состояние'] == 'Доставлен')
                # | (delivery['Состояние'] != 'Самовывоз')
                | (delivery['Статус заказа'] == 'Доставлен')
             ),
            'is_delivered'] = 1

        delivery['status'] = delivery['Состояние'] + '|' + delivery['Статус заказа']
        delivery.rename(columns={
            'Номер заказа': 'id',
            'Дата доставки': 'dt',
            'Оценочная  сумма': 'delivery_cnt'
        }, inplace=True)
        delivery['status'] = delivery['Состояние'] + ';' + delivery['Статус заказа']
        delivery['delivery_cnt'] = delivery['delivery_cnt'].str.replace(',00','').fillna(0).astype(int, errors='ignore') / 20
        delivery['dt'] = pd.to_datetime(delivery['dt'], dayfirst=True)
        delivery['delivery_type'] = 1
        delivery = delivery[['id', 'delivery_cnt', 'dt', 'is_delivered', 'status', 'delivery_type']]

        orders = read_df('select distinct id, vsp, dep_id from SIMS_ORDERS')
        delivery = delivery.merge(
            orders,
            on='id',
            how='left'
        )

    if save_db:
        save_df(delivery[['id', 'dt', 'dep_id', 'vsp', 'delivery_cnt', 'delivery_type', 'status']], 'SIMS_DELIVERY_tmp')
        run_sql('''
                    insert or replace into SIMS_DELIVERY(id, dt, dep_id, vsp, delivery_cnt, delivery_type, status)
                    select id, dt, dep_id, vsp, delivery_cnt, delivery_type, status from SIMS_DELIVERY_tmp
                ''')

    return delivery


def load_orders(path_to_file='', filter_dt=None, save_db=True):

    orders = pd.read_csv(path_to_file, sep=';', encoding='utf-8', quoting=1)
    orders = orders[[
        'Код',
        'Краткое описание',
        'Описание',
        'Время регистрации',
        'Статус',
        'Внутренний Клиент',
        'Организация',
        'ID подразделения ВК',
    ]]
    orders.columns = ['id', 'short_desc', 'desc', 'dttm', 'status', 'client', 'tb', 'dep_id']
    orders['dttm'] = pd.to_datetime(orders['dttm'], dayfirst=True)  # скорее всего дата загрузилась в виде строки, привожу к дате

    # фильтрую выгрузку, если заданы параметры фильтрации
    if filter_dt:
        orders = orders[orders['dttm'] >= filter_dt]

    # парсинг Описания
    orders['order_count'] = orders['desc'].str.extract(r'Количество ...-карт для заказа: (\d+)', expand=True)
    orders['address'] = orders['desc'].str.extract(r'Здание: (.+)', expand=False)
    re_str = re.compile(r'Заказ ...-карт СберМобайл.+')
    orders['address'] = orders['address'].apply(lambda x: re.sub(re_str, '', x))
    orders['vsp_src'] = orders['desc'].str.extract(r'ТБ-ГОСБ-ВСП: (\S{3,15})', expand=False)
    orders['phone'] = orders['desc'].str.extract(r'Мобильный номер телефона: (.+) Здание:', expand=False)
    orders['reason'] = orders['desc'].str.extract(r'Причина подкрепления: (.+) Остатки ... карт в ВСП на начало дня:', expand=False)
    orders['balance'] = orders['desc'].str.extract(r'Остатки ... карт в ВСП на начало дня: (\d+) ТБ-ГОСБ-ВСП:', expand=False)

    orders['client_short'] = orders['client'].str.extract(r' ([a-zA-Zа-яА-Я\- ]+)', expand=False)

    # проставляю 0 если срочный заказ, 1 - если автопополнение
    orders['order_type'] = orders['short_desc'].apply(lambda x: 0 if x == 'Заказ СИМ-карт СберМобайл' else 1)

    orders['order_count'] = orders['order_count'].apply(lambda x: 0 if pd.isnull(x) else int(x))
    orders['balance'] = orders['balance'].apply(lambda x: 0 if pd.isnull(x) else int(x))

    # функция для корректировки номера ВСП
    def vsp_mod(x):
        _vsp = str(x)
        if '-' in _vsp:
            _vsp = _vsp.split('-')
            if len(_vsp) >= 3:

                vsp_left = _vsp[1]
                vsp_right = _vsp[2]

                if vsp_left.isdigit():
                    vsp_left = vsp_left.zfill(4)
                if vsp_right.isdigit():
                    vsp_right = vsp_right.zfill(5)

                _vsp = vsp_left + '_' + vsp_right
            else:
                _vsp = '_'.join(_vsp)
        return _vsp

    orders['vsp'] = orders['vsp_src'].apply(vsp_mod)

    # опеределяю дату для загрузки с этой даты информации из базы по старым заявкам

    if save_db:
        save_df(orders[[
                    'id', 'dttm', 'dep_id', 'vsp', 'order_count', 'balance', 'order_type', 'status',
                    'address', 'client_short', 'phone',
                    ]], 'SIMS_ORDERS_tmp')
        run_sql('''
            insert or replace into SIMS_ORDERS(id, dttm, dep_id, vsp, order_count, balance, order_type, status, address, client_short, phone)
            select id, dttm, dep_id, vsp, order_count, balance, order_type, status, address, client_short, phone from SIMS_ORDERS_tmp
        ''')

    return orders


def get_orders_in_work():
    orders = read_df()


def load_sales(dt_max=None, save_db=True):

    if not dt_max:
        dt_max = read_df('select max(dt) - 14 as mdt from SIMS_expense')
        if dt_max.empty:
            dt_max = '2015-01-01'
        else:
            dt_max = dt_max['mdt'][0]

    sql = read_sql_command(r'C:\work\Portal\apps\sims\sql\sales.sql', dt=dt_max)
    conn = pyodbc.connect(TERA_STR_CONN)
    sales = pd.read_sql(sql, conn)
    conn.close()
    conn = None
    sales['tab_num'] = sales['tab_num'].astype(str, errors='ignore').str.replace('.0', '')
    sales['vsp'] = sales['vsp'].apply(
        lambda x:
        x[x.find('_') + 1:x.rfind('_')].zfill(4) + '_' + x[x.rfind('_') + 1:].zfill(5)
        if type(x) == str
        else ''
    )
    sales['vsp'] = sales['vsp'].apply(lambda x: '8647' + x[4:] if x[:4] == '0029' else x)
    if len(sales) > 0:
        run_sql('''delete from SIMS_expense where dt >= '{}'
                '''.format(dt_max))
        save_df(sales, 'SIMS_expense', 'append')

    return sales


def save_df(df, tbl_name, if_exists='replace'):
    try:
        conn = sqlite3.connect(SQL_DATABASE)
        df.to_sql(name=tbl_name, con=conn, if_exists=if_exists, index=False)
        conn.close()
    except Exception as err:
        print(err)


def read_df(sql='', tbl_name=''):
    if tbl_name:
        sql = 'select * from {}'.format(tbl_name)
    try:
        conn = sqlite3.connect(SQL_DATABASE)
        df = pd.read_sql(sql, con=conn)
        conn.close()
    except Exception as err:
        print(err)
        return pd.DataFrame()
    return df


def run_sql(sql):
    try:
        conn = sqlite3.connect(SQL_DATABASE)
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as err:
        print(err)


def read_sql_command(src_path, **kwargs):
    with open(src_path, 'r') as f:
        sql = f.read()
        for kwarg in kwargs:
            sql = sql.replace('{' + kwarg + '}', str(kwargs[kwarg]))
    return sql


if __name__ == '__main__':
    # orders = load_orders(path_to_file = r'\\Braga101\Vol2\SUDR_PCP_BR\SIMS\sources\orders.csv')
    # delivery = load_delivery(delivery_type=0, path_to_file=r'\\Braga101\Vol2\SUDR_PCP_BR\SIMS\sources\delivery.xlsx')
    # delivery = load_delivery(delivery_type=1, path_to_file=r'\\Braga101\Vol2\SUDR_PCP_BR\SIMS\sources\report.xls')
    sales = load_sales()
