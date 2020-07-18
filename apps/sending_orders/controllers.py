from flask import (
    render_template,
    request,
    jsonify,
    make_response,
    Blueprint,
)


senor = Blueprint('senor', __name__, url_prefix='/senor', static_folder='static', template_folder='templates')


@senor.route('/')
def index():
    return render_template('sending_orders.html', title='Название страницы')


@senor.route('/run_script', methods=['POST'])
def run_script():
    req = request.get_json()
    res = make_response(jsonify('Все ок'), 200)

    return res
