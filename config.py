import os
from dotenv import load_dotenv
from datetime import timedelta

load_dotenv()

# Database configuration - Priority to DATABASE_URL (Neon)
SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')

# Fix for postgres:// vs postgresql:// issue (Render compatibility)
if SQLALCHEMY_DATABASE_URI and SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
    SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)

# Fallback to individual environment variables if DATABASE_URL is not set
if not SQLALCHEMY_DATABASE_URI:
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{os.environ.get('DB_USER')}:{os.environ.get('DB_PASS')}"
        f"@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME')}"
    )

SQLALCHEMY_TRACK_MODIFICATIONS = False
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev123!@#supersecret')

# Production settings
DEBUG = os.environ.get('FLASK_ENV') == 'development'

# Session Security Settings
PERMANENT_SESSION_LIFETIME = timedelta(hours=8)  # Session expires after 8 hours
SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True  # Prevent XSS attacks
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
