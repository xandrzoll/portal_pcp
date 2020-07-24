from flask import (
    render_template,
    request,
    jsonify,
    make_response,
    Blueprint,
    redirect,
    url_for
)
from .data_worker import (
    read_df,
    load_orders,
    load_delivery,
    load_sales,
    calculate_balance,
    orders_worker
)

# здесь создаем blueprint. Его потом подключаем в файле manage.py в корне
# название senor, префикс /senor, т.е. в приложении все роуты к нему будут обрабатываться как /senor/*
# , но в роутах этого модуля префикс опускается
sims = Blueprint('sims', __name__, url_prefix='/sims', static_folder='static', template_folder='templates')


# отрисовываю страницу, она доступна по ссылке http://localhost:5000/sims/
@sims.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        orders_info, delivery_info, sales_info = get_values_for_sims_page()
        return render_template('sims.html', title='Сим-карты СберМобайл',
                               orders_info=orders_info,
                               delivery_info=delivery_info,
                               sales_info=sales_info)

    if request.form.get('orders') == 'on':
        print('запускаю загрузку заявок')
        load_orders(path_to_file = r'\\Braga101\Vol2\SUDR_PCP_BR\SIMS\sources\orders.csv')

    if request.form.get('delivery') == 'on':
        print('запускаю загрузку поставок')
        load_delivery(delivery_type=0, path_to_file=r'\\Braga101\Vol2\SUDR_PCP_BR\SIMS\sources\delivery.xlsx')
        load_delivery(delivery_type=1, path_to_file=r'\\Braga101\Vol2\SUDR_PCP_BR\SIMS\sources\report.xls')

    if request.form.get('sales') == 'on':
        print('запускаю загрузку продаж')
        load_sales()

    if request.form.get('balances') == 'on':
        print('запускаю загрузку остатков ВСП')
        calculate_balance(save_db=True, check_last_balance=False)

    if request.form.get('orders_worker') == 'on':
        print('запускаю обновление check_orders')
        orders_worker()

    return redirect(url_for('sims.index'))


# функция для отлавливания запросов со страницы, те которые отправляются функцией fetch
@sims.route('/run_script', methods=['POST'])
def run_script():
    # получаем содержимое запроса
    req = request.get_json()

    # содержимое запроса используется в запуске функции. Функцию нужно импортировать и запустить ниже
    # your code is here

    # формируем ответ для отрисовки на странице
    res = make_response(jsonify('Все ок'), 200)

    return res


def get_values_for_sims_page():
    orders_info = read_df("""
                select 
                  sum(case when dttm >= date('now', 'start of month') then 1 else 0 end) orders_current,
                  sum(case when dttm >= date('now', 'start of month', '-1 month') and dttm < date('now', 'start of month') then 1 else 0 end) orders_prev,
                  strftime('%d.%m.%Y', max(dttm)) dt_order
                from sims_orders
        """)
    orders_info = list(orders_info.values[0])
    delivery_info = read_df("""
                select 
                  sum(case when dt >= date('now', 'start of month') then 1 else 0 end) delivery_current,
                  sum(case when dt >= date('now', 'start of month', '-1 month') and dt < date('now', 'start of month') then 1 else 0 end) delivery_prev,
                  strftime('%d.%m.%Y', max(dt)) dt_delivery
                from sims_delivery
        """)
    delivery_info = list(delivery_info.values[0])

    sales_info = read_df("""
                select 
                  strftime('%d.%m.%Y', max(dt)) dt_sales
                from sims_expense
        """)
    sales_info = list(sales_info.values[0])

    return orders_info, delivery_info, sales_info