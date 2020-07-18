import os
from flask import Flask


def create_app():
    app_ = Flask(__name__)
    app_.config.from_object(os.environ.get('APP_PORTAL_SETTINGS') or 'config.AlphaProdConfig')

    import apps.main.controllers as main
    import apps.run_scripts.controllers as run_scripts

    # здесь добавлять новые приложения
    app_.register_blueprint(main.main)
    app_.register_blueprint(run_scripts.scrpt)
    # в config['base_header'] приложения содержатся все элементы для базового заголовка
    app_.config['base_header'] = [
        {'name': 'Главная', 'href': '/'},
        {'name': 'Режимы работы', 'href': '/worktime'},
        {'name': 'Сим-карты', 'href': '#'},
        {'name': 'SQL Admin', 'href': '/SQL_Admin'},
    ]

    return app_


app = create_app()


# from celery import Celery
#
# celery = Celery(app.name, broker='redis://localhost:6379/0')
# celery.conf.update(app.config)


@app.context_processor
def insert_header():
    return dict(header_list=app.config['base_header'])


if __name__ == '__main__':
    app.run(app.config['HOST_APP'])
