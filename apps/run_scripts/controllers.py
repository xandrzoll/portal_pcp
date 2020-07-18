from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    make_response,
    redirect,
    Blueprint,
    session,
    flash,
    url_for
)


scrpt = Blueprint('scrpt', __name__, url_prefix='/run_script')


# @scrpt.route('/')
# def index():
#     return render_template('run_script/run_scrt.html', title='Новая')


@scrpt.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'GET':
        return render_template('index.html', email=session.get('email', ''))
    email = request.form['email']
    session['email'] = email

    if request.form['submit'] == 'Send':
        # send right away
        send_async_email.delay(msg)
        flash('Sending email to {0}'.format(email))
    else:
        # отправка почты через минуту
        send_async_email.apply_async(args=[msg], countdown=60)
        flash('An email will be sent to {0} in one minute'.format(email))

    return redirect(url_for('index'))


def send_async_email():
    import time
    time.sleep(30)
    print('Ok')
