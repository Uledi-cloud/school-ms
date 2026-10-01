import os
from datetime import timedelta


class Config:
    # ===================== CORE =====================
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-me-in-production')

    # ===================== DATABASE =====================
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///school.db')
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {'pool_pre_ping': True, 'pool_recycle': 300}

    # ===================== SESSIONS =====================
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'

    # ===================== CSRF =====================
    WTF_CSRF_ENABLED = True

    # ===================== SETUP =====================
    SETUP_TOKEN = 'setup-secret-token'

    # ===================== SMS (Africa's Talking) =====================
    AT_USERNAME = os.environ.get('AT_USERNAME', '')
    AT_API_KEY = os.environ.get('AT_API_KEY', '')
    AT_SENDER_ID = os.environ.get('AT_SENDER_ID', '')

    # ===================== EMAIL (SMTP) =====================
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')
    MAIL_USE_TLS = True
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@school.com')

    # ===================== SCHOOL DEFAULTS =====================
    # These are fallbacks. The real school data lives in the `School` database table,
    # editable from /developer/school after login.
    SCHOOL_NAME = os.environ.get('SCHOOL_NAME', 'My ELITE Academia Primary School')
    SCHOOL_ADDRESS = os.environ.get('SCHOOL_ADDRESS', 'P.O. Box 123, Tanzania')
    SCHOOL_PHONE = os.environ.get('SCHOOL_PHONE', '+255 700 000 000')