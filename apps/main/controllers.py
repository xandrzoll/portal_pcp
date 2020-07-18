from multiprocessing import Process
from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    make_response,
    redirect,
    Blueprint,
)

from db.db_admin import fetch_data, check_active_tasks
from apps.worktime import worktime_reports_for_site


main = Blueprint('main', __name__, url_prefix='')


@main.route('/')
def index():
    return render_template('index.html', title='Главная')


@main.route('/worktime')
def worktime_page():
    # tasks = check_active_tasks()
    return render_template('worktime.html', title='Режимы работы')


@main.route('/SQL_Admin')
def sql_page():
    return render_template('sql_admin.html', title='SQL Admin')


@main.route('/run_sql_script', methods=['POST'])
def run_sql():
    req = request.get_json()
    print(req)
    data = fetch_data(req)
    res = make_response(jsonify(data), 200)

    return res


@main.route('/apps/<app_name>', methods=['POST'])
def run_app(app_name):
    req = request.get_json()

    if app_name == 'worktime':
        tasks = check_active_tasks()
        if tasks:
            return make_response('OK', 200)
        # sql = '''insert into APP_TASKS (dttm, task_name, status) values (datetime('now', 'localtime'), 'Режимы работы', 'active')
        # '''
        # id_row = fetch_data(sql)['data']
        worktime_reports_for_site()
        p = Process(target=worktime_reports_for_site, args=(True, True, False, '', '', False, False), kwargs={'id_row': id_row})
        p.start()

        res = make_response('OK', 200)
    return res

