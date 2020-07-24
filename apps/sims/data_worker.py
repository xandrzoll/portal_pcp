import pandas as pd
import re
import sqlite3
import pyodbc
import datetime
from config import cnf


SQL_DATABASE = cnf.SQL_DATABASE
TERA_STR_CONN = cnf.TERA_STR_CONN


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
        dt_max = read_df("select date(max(dt), '-14 days') as mdt from SIMS_expense")
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


def calculate_balance(dt_end='', save_db=True, check_last_balance=True):
    if not dt_end:
        dt_end = read_df('''
            select max(dttm) as mdt from SIMS_orders
            union all
            select max(dt) as mdt from SIMS_delivery
            union all
            select max(dt) as mdt from SIMS_expense
        ''').min()[0]
        print(dt_end)

    if check_last_balance:
        last_bal = read_df("select vsp, dt, balance from SIMS_balances where dt = '2020-01-01'")
        dt_start = '2020-01-01'
    else:
        dt_start = '2015-01-01'

    delivery = read_df("select distinct vsp, dt, delivery_cnt as delivery from SIMS_delivery where dt > '{}'".format(dt_start))
    sales = read_df("select vsp, dt, sum(expense_cnt) as sales from SIMS_expense where dt > '{}' group by vsp, dt".format(dt_start))
    orders = read_df("""
            select id as order_id, vsp, dt,  order_balance from (
                select id, vsp, date(dttm) as dt, balance as order_balance, row_number() over (partition by vsp, date(dttm) order by dttm desc) as rn  from SIMS_orders
                where dttm > '{}'
            ) as T1
            where rn = 1
    """.format(dt_start))

    sales['delivery'], sales['order_balance'], sales['is_order_balance'], sales['balance'] = 0, 0, 0, 0
    delivery['sales'], delivery['order_balance'], delivery['is_order_balance'], delivery['balance'] = 0, 0, 0, 0
    orders['delivery'], orders['sales'], orders['is_order_balance'], orders['balance'] = 0, 0, 1, 0

    if check_last_balance:
        last_bal['delivery'], last_bal['order_balance'], last_bal['is_order_balance'], last_bal['sales'] = 0, 0, 0, 0

    cols = ['vsp', 'dt', 'sales', 'delivery', 'order_balance', 'is_order_balance', 'balance']

    if check_last_balance:
        data = sales[cols].append([delivery[cols], orders[cols], last_bal[cols]])
    else:
        data = sales[cols].append([delivery[cols], orders[cols]])

    data = data.groupby(['vsp', 'dt'])[cols[2:]].sum().reset_index()
    data = data.sort_values(by=['vsp', 'dt'])
    data.fillna(0, inplace=True)

    global last_vsp
    last_vsp = data.loc[0, 'vsp']
    global balance
    balance = 0

    def cumulative_sum(x):
        global balance
        global last_vsp

        if x['is_order_balance'] == 1:
            balance = x['order_balance']
        elif x['vsp'] == last_vsp:
            balance += x['delivery'] - x['sales'] + x['balance']

        else:
            balance = x['delivery'] - x['sales'] + x['balance']

        if balance < 0:
            balance = 0

        last_vsp = x['vsp']
        return balance

    data['balance'] = data.apply(lambda x: cumulative_sum(x), axis=1)
    data = data[data['dt'] <= dt_end]
    data['real_balance'] = data.loc[data['vsp'].shift(-1) == data['vsp'], 'balance']
    data['real_balance'] = data['real_balance'].shift() - data['sales'] + data['delivery']

    last = data.groupby('vsp')['balance'].last().reset_index()
    last['dt'] = dt_end

    if save_db:
        run_sql('delete from SIMS_balances where dt = {}'.format(dt_end))
        save_df(last, 'SIMS_balances', if_exists='append')

    return [last, data]


def orders_worker():
    sql = '''
        select 
            T1.id, 
            T1.dttm, 
            T1.dep_id, 
            T1.vsp, 
            T1.status, 
            T1.address, 
            T1.client_short, 
            T1.phone, 
            T1.order_count,
            T1.balance as balance_from_order,
            0 as calc_balance,
            (select id from SIMS_ORDERS where dttm >= date(T1.dttm, '-14 day') and (vsp=T1.vsp or dep_id=T1.dep_id)  and id <> T1.id order by dttm desc limit 1) as id_prev_14,
            (select id from SIMS_DELIVERY where vsp=T1.vsp order by dt desc limit 1) as id_prev_delivery,
            (select dt from SIMS_DELIVERY where vsp=T1.vsp order by dt desc limit 1) as dt_prev_delivery,
            (select delivery_cnt from SIMS_DELIVERY where vsp=T1.vsp order by dt desc limit 1) as count_prev_delivery,
            (select sum(delivery_cnt) as d from SIMS_DELIVERY where vsp=T1.vsp) as delivery_all,
            (select sum(expense_cnt) as sales from SIMS_expense where vsp = T1.vsp) as sales_all,
            (select sum(case when dt >= date('now', 'start of month') then expense_cnt else 0 end) as sales from SIMS_expense where vsp = T1.vsp) as sales_current,
            (select sum(case when dt >= date('now', 'start of month', '-1 month') and dt <= date('now', 'start of month', '-1 day') then expense_cnt else 0 end) as sales from SIMS_expense where vsp = T1.vsp) as sales_prev1,
            (select sum(case when dt >= date('now', 'start of month', '-2 month') and dt <= date('now', 'start of month', '-1 month', '-1 day') then expense_cnt else 0 end) as sales from SIMS_expense where vsp = T1.vsp) as sales_prev2
        from SIMS_ORDERS as T1
        where T1.status not in ('Закрыто', 'Выполнено') and order_type = 0
    '''
    data = read_df(sql)
    data['dt'] = data['dttm'].str[:10]
    balances = calculate_balance(save_db=False)[1]
    balances = balances.merge(
        data[['vsp', 'dt']],
        on='vsp',
        suffixes=['', '_order'],
        how='inner'
    )
    balances = balances[pd.to_datetime(balances['dt']) < pd.to_datetime(balances['dt_order'])]
    balances = balances.groupby('vsp')['balance'].last().reset_index()

    data = data.merge(
        balances[['vsp','balance']],
        on='vsp',
        how='left',
    )
    data['calc_balance'] = data['balance']
    data.drop(['balance'], axis=1)

    def algoritmic_solution(x):
        algo_status = ''

        if x['id_prev_14']:
            algo_status += 'Заявка до 14 дней; '

        now_mon = datetime.date.today().strftime('%Y-%m')
        if x['dt_prev_delivery']:
            if now_mon == x['dt_prev_delivery'][:6]:
                algo_status += 'В этом месяце уже была доставка; '

        if x['calc_balance'] >= x['balance_from_order'] * 1.5 and x['calc_balance'] > 90:
            algo_status += 'Расчетный остаток больше; '

        return algo_status

    data['algoritmic_solution'] = data.apply(algoritmic_solution, axis=1)

    data.to_excel(r'\\Braga101\Vol2\SUDR_PCP_BR\SIMS\sources\orders_data_new.xlsx')


def save_df(df, tbl_name, if_exists='replace'):
    try:
        conn = sqlite3.connect(SQL_DATABASE)
        df.to_sql(name=tbl_name, con=conn, if_exists=if_exists, index=False)
        conn.commit()
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
    # sales = load_sales()
    last = calculate_balance(save_db=True, check_last_balance=False)
    # orders_worker()
