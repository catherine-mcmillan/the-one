import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-please-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:////data/app.db' if os.environ.get('FLASK_ENV') == 'production' else 'sqlite:///app.db'
    SQLITE_DB = '/data/app.db' if os.environ.get('FLASK_ENV') == 'production' else 'app.db'

    def __init__(self):
        if os.environ.get('FLASK_ENV') == 'production':
            self.SQLALCHEMY_DATABASE_URI = 'sqlite:////data/app.db'
            self.SQLITE_DB = '/data/app.db'
        else:
            self.SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
            self.SQLITE_DB = 'app.db' 