import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///school.db')
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_recycle': 300}

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    WTF_CSRF_ENABLED = True

    AT_USERNAME = os.environ.get('AT_USERNAME', '')
    AT_API_KEY = os.environ.get('AT_API_KEY', '')
    AT_SENDER_ID = os.environ.get('AT_SENDER_ID', '')

    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_USE_TLS = True
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@school.com')

    SETUP_TOKEN = os.environ.get('SETUP_TOKEN', 'setup-secret-token')
    SCHOOL_NAME = os.environ.get('SCHOOL_NAME', 'Your School Name')
    SCHOOL_ADDRESS = os.environ.get('SCHOOL_ADDRESS', 'P.O. Box 000, Tanzania')
    SCHOOL_PHONE = os.environ.get('SCHOOL_PHONE', '+255 000 000 000')