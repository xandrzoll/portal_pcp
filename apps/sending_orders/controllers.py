from flask import (
    render_template,
    request,
    jsonify,
    make_response,
    Blueprint,
)


# здесь создаем blueprint. Его потом подключаем в файле manage.py в корне
# название senor, префикс /senor, т.е. в приложении все роуты к нему будут обрабатываться как /senor/*
# , но в роутах этого модуля префикс опускается
senor = Blueprint('senor', __name__, url_prefix='/senor', static_folder='static', template_folder='templates')


# отрисовываю страницу, она доступна по ссылке http://localhost:5000/senor/
@senor.route('/')
def index():
    return render_template('sending_orders.html', title='Название страницы')


# функция для отлавливания запросов со страницы, те которые отправляются функцией fetch
@senor.route('/run_script', methods=['POST'])
def run_script():
    # получаем содержимое запроса
    req = request.get_json()

    # содержимое запроса используется в запуске функции. Функцию нужно импортировать и запустить ниже
    # your code is here

    # формируем ответ для отрисовки на странице
    res = make_response(jsonify('Все ок'), 200)

    return res
