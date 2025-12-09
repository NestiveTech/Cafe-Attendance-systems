import os
from pathlib import Path
import dj_database_url # ADDED: For production PostgreSQL support
from whitenoise.storage import CompressedManifestStaticFilesStorage # ADDED: For WhiteNoise static file storage

# --- CRITICAL FIX FOR LOCALHOST OAUTH ---
# This is kept here for local development consistency, even if manage.py also has it.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

BASE_DIR = Path(__file__).resolve().parent.parent

# --- PRODUCTION READY CHANGES ---
# Use environment variable for SECRET_KEY (MANDATORY for Render)
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-(y#njkh4eny7bb8e8c=2w(^gb%8d1(w413y!41f9bi!#n354ha')

# Set DEBUG from environment variable. Defaults to False (production).
DEBUG = os.environ.get('DEBUG', 'False') == 'True' 

# ALLOWED_HOSTS for Render deployment. Use WEB_HOST env var.
ALLOWED_HOSTS = [
    '127.0.0.1', 
    'localhost', 
    os.environ.get('WEB_HOST', 'cafe-terrain-attendance-system.onrender.com') # Replace default with your Render domain
]
# --------------------------------

# REDIRECT_URI is typically handled in code and credentials.json, but keep the original config clean
# REDIRECT_URI = os.environ.get('REDIRECT_URI', 'http://127.0.0.1:8000/oauth2callback/')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'attendance',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # ADDED: WhiteNoise middleware MUST be placed directly after SecurityMiddleware
    'whitenoise.middleware.WhiteNoiseMiddleware', 
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'cafe_terrain.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'cafe_terrain.wsgi.application'

# 5. DATABASE CONFIG FOR RENDER POSTGRESQL 
# Use dj_database_url to configure connection using the DATABASE_URL environment variable 
# provided by Render, falling back to SQLite for local development.
DATABASES = {
    'default': dj_database_url.config(
        default='sqlite:///' + str(BASE_DIR / 'db.sqlite3'),
        conn_max_age=600 # Connection pooling setting
    )
}
# ---------------------------------------------

LANGUAGE_CODE = 'en-us'

# --- SPEED & TIMEZONE FIX ---
TIME_ZONE = 'Asia/Kolkata'  # Set to Indian Standard Time
USE_I18N = True
USE_TZ = True              # Enable Timezone support
# ---------------------------

STATIC_URL = 'static/'

# --- STATIC FILE CONFIGURATION FOR WHITENOISE ---
# This is the directory where `collectstatic` will put all static files.
STATIC_ROOT = BASE_DIR / 'staticfiles' 
# Tell WhiteNoise to use the compressed storage engine for better performance
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
# ------------------------------------------------

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'login'