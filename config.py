import os


class Config:
    DEBUG = False
    CSRF_ENABLED = True
    SECRET_KEY = 'YOUR_RANDOM_SECRET_KEY'
    SQL_DATABASE = os.environ.get('APP_PORTAL_DB') or 'db/database.db'


class AlphaProdConfig(Config):
    DEBUG = False
    HOST_APP = '10.222.124.199'
    SQL_DATABASE = r'db/database.db'
    TERA_STR_CONN = 'TDSB14'


class SigmaTestConfig(Config):
    DEBUG = True
    HOST_APP = 'localhost'
    SQL_DATABASE = r'db/database.db'
    TERA_STR_CONN = ''


cnf = SigmaTestConfig()
