import sqlite3


MAX_ROWS_RETURN = 200


def fetch_data(sql):
    data = ''
    conn = sqlite3.connect(r'db/database.db')
    cursor = conn.cursor()
    try:
        if sql[:6] == 'select':
            cursor.execute(sql)
            data = cursor.fetchall()
            data = {
                'type': 'select',
                'data': {i: [x[0]] + [y[i] for y in data[:MAX_ROWS_RETURN]] for i, x in enumerate(cursor.description)}
            }

        elif sql[:6] == 'insert':
            cursor.execute(sql)
            conn.commit()
            data = {
                'type': 'insert',
                'data': str(cursor.lastrowid)
            }

        elif sql[:6] == 'update':
            cursor.execute(sql)
            conn.commit()
            data = {
                'type': 'update',
                'data': str(cursor.rowcount)
            }

        elif sql[:6] == 'delete':
            cursor.execute(sql)
            conn.commit()
            data = {
                'type': 'delete',
                'data': str(cursor.rowcount)
            }
        elif sql[:6] == 'create':
            cursor.execute(sql)
            conn.commit()
            data = {
                'type': 'create',
                'data': 'Table created'
            }

    except Exception as err:
        data = {'type': 'error', 'data': str(err)}
        print(err)
    finally:
        cursor.close()
        conn.close()

    if not data:
        data = {'type': 'error', 'data': 'script not parsed'}

    return data


def check_active_tasks():
    conn = sqlite3.connect(r'db/database.db')
    cursor = conn.cursor()
    try:
        sql = '''
        select * from APP_TASKS where status = 'active'
        '''
        cursor.execute(sql)
        data = cursor.fetchall()
        return data
    finally:
        cursor.close()
        conn.close()


def create_table():
    conn = sqlite3.connect(r'db/database.db')
    cursor = conn.cursor()

    cursor.execute(
        """CREATE TABLE APP_TASKS
          (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, dttm text, task_name text, status text)
        """
    )

    cursor.execute(
        """insert into SIMS_DELIVERY
            values ('SD003', '2020-03-03', '103813123', 100)
        """
    )
    conn.commit()

    sql = '''
        update sims_delivery
        set cnt = 900
        where depid = '103813123'
    '''
    cursor.execute(sql)

    sql = '''
            delete from sims_delivery
            where depid = '103813123'
        '''
    cursor.execute(sql)

    sql = 'select * from sims_delivery'
    cursor.execute(sql)
    data = cursor.fetchall()

    sql = 'alter table SIMS_expense add pos_gr Text'

    cursor.close()
    conn.close()


def read_sql_command(src_path, **kwargs):
    with open(src_path, 'r') as f:
        sql = f.read()
        for kwarg in kwargs:
            sql = sql.replace('{' + kwarg + '}', str(kwargs[kwarg]))
    return sql


def insert_data(data, tbl_name):
    conn = sqlite3.connect(r'db/database.db')
    cursor = conn.cursor()
    data.to_sql(tbl_name, con=conn, index=False, if_exists='append')
    cursor.close()
    conn.close()


def loads_from_TD(data_type):
    if data_type == 'sales':
        dt_max = fetch_data('select max(dt) - 7 as mdt from SIMS_expense')['data'][0][1]
        if not dt_max:
            dt_max = '2015-01-01'
        fetch_data('delete from SIMS_expense where dt >=\'{}\''.format(dt_max))
        # sql = read_sql_command(r'db/sql/sales.sql', dt=dt_max)
        # tera = Tera('dsn=TDSB14')
        # data = tera.get_data(sql)
        # tera.close()
        # tera = None
        # data['tab_num'] = data['tab_num'].astype(str).str.replace('.0', '')
        # insert_data(data, 'SIMS_expense')


def decorator_update_row(func):
    def wrapper(*args, **kwargs):
        id_row = kwargs.get('id_row')
        if id_row:
            kwargs.pop('id_row')
            val = func(*args, **kwargs)

            from db.db_admin import fetch_data

            sql = '''update APP_TASKS set status = 'done' where id={}
                        '''.format(id_row)
            id_row = fetch_data(sql)
        else:
            val = func(*args, **kwargs)
        return val
    return wrapper


if __name__ == '__main__':
    loads_from_TD('sales')
