"""
Django settings for restaurant_booking project - COMPLETE VERSION WITH EMAIL NOTIFICATIONS

Generated by 'django-admin startproject' using Django 5.2.1.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.2/ref/settings/
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure--%m5*^=v+k0m+5892wzichk$_rhekn#-t+_e=2#4(y*qa0orvx'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

# FIXED: Remove duplicate assignment
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# Application definition
INSTALLED_APPS = [
    'jazzmin',  # Modern admin theme
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',  # Django REST Framework
    'corsheaders',     # CORS pour React
    'reservations',    # Votre app
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',  # CORS en premier
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'restaurant_booking.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'restaurant_booking.wsgi.application'

# Database - PostgreSQL Configuration (Production Database)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'restaurant_booking',
        'USER': 'postgres',
        'PASSWORD': 'simanjali',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Alternative: SQLite Configuration (commented out - for development only)
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/
LANGUAGE_CODE = 'fr-fr'  # Français
TIME_ZONE = 'Africa/Casablanca'

USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ]
}

# CORS Configuration pour React
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React development server
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True

# For development - allow all origins (easier debugging)
CORS_ALLOW_ALL_ORIGINS = True

# CORS headers configuration
CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# ==========================================
# EMAIL CONFIGURATION FOR RESTO PÊCHEUR
# ==========================================

# Email Backend Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

# Gmail SMTP Configuration
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'simanjali8@gmail.com'  # Replace with your Gmail
EMAIL_HOST_PASSWORD = 'kili bgnf rlhs nfrr'  # Replace with your Gmail App Password
EMAIL_USE_SSL = False  # Use TLS instead of SSL for Gmail

# Default sender information
DEFAULT_FROM_EMAIL = 'Resto Pêcheur <simanjali8@gmail.com>'
SERVER_EMAIL = 'Resto Pêcheur <simanjali8@gmail.com>'

# Email timeout settings
EMAIL_TIMEOUT = 60

# For development: Print emails to console (uncomment to test without real emails)
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Email logging for debugging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'email.log',
        },
    },
    'loggers': {
        'django.core.mail': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'reservations.utils.email_utils': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Create logs directory if it doesn't exist
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

# Alternative Email Providers (commented out - uncomment if needed)
# 
# # Outlook/Hotmail Configuration
# EMAIL_HOST = 'smtp-mail.outlook.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@outlook.com'
# EMAIL_HOST_PASSWORD = 'your-password'
#
# # Yahoo Configuration
# EMAIL_HOST = 'smtp.mail.yahoo.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@yahoo.com'
# EMAIL_HOST_PASSWORD = 'your-app-password'

# ==========================================
# JAZZMIN ADMIN THEME CONFIGURATION
# ==========================================

JAZZMIN_SETTINGS = {
    "site_title": "",  # EMPTY
    "site_header": "",  # EMPTY 
    "site_brand": "",  # EMPTY
    "site_logo": "admin/img/logo.png",  # ADD YOUR LOGO
    "login_logo": "admin/img/logo.png",  # ADD LOGO TO LOGIN TOO
    "site_logo_classes": "brand-image-xl",  # MAKE IT BIGGER
    "welcome_sign": "",  # EMPTY
    "copyright": "",  # EMPTY
    
    # Ocean theme
    "theme": "cerulean",
    "dark_mode_theme": None,
    
    # Custom styling
    "custom_css": "admin/css/theme.css", 
    "custom_js": None,
    
    # HIDE USER INFO FROM SIDEBAR
    "show_ui_builder": False,
    "show_sidebar": True,
    "navigation_expanded": True,
    
    # CLEAN NAVIGATION - Remove ALL branding
    "topmenu_links": [],  # EMPTY ARRAY
    
    # Keep user menu minimal - only in top-right
    "usermenu_links": [
        {"name": "Profil", "url": "admin:auth_user_change", "icon": "fas fa-user"},
        {"model": "auth.user"}
    ],
    
    # Menu ordering for single restaurant
    "order_with_respect_to": ["reservations", "auth"],
    
    # Icons for your models
    "icons": {
        "auth": "fas fa-anchor",
        "auth.user": "fas fa-user-tie", 
        "reservations.reservation": "fas fa-calendar-check",
        "reservations.notification": "fas fa-bell",  # NEW: Notification icon
        "reservations.timeslot": "fas fa-clock",
        "reservations.specialdate": "fas fa-calendar-alt",
        "reservations.restaurantinfo": "fas fa-cog",
    },
    
    "default_icon_parents": "fas fa-fish",
    "default_icon_children": "fas fa-circle",
    
    "related_modal_active": False,
    
    # Hide unnecessary models for single restaurant
    "hide_apps": [],
    "hide_models": [
        "auth.Group",  # Single admin, no groups needed
    ],
    
    "changeform_format": "horizontal_tabs",
    
    # CUSTOM CSS AND JS TO HIDE USER PANEL
    "custom_css": "admin/css/theme.css",
    
    # Additional UI settings to minimize user info display
    "user_avatar": None,  # Don't show user avatar
}

# ==========================================
# NOTIFICATION SYSTEM SETTINGS
# ==========================================

# Notification settings
NOTIFICATION_SETTINGS = {
    'AUTO_SEND_EMAILS': True,  # Set to False to disable automatic emails
    'EMAIL_RETRY_ATTEMPTS': 3,  # Number of retry attempts for failed emails
    'NOTIFICATION_RETENTION_DAYS': 30,  # How long to keep read notifications
}

# Restaurant Information (for email templates)
RESTAURANT_INFO = {
    'NAME': 'Resto Pêcheur',
    'ADDRESS': 'Route De Tafraout Quartier Industriel, Tiznit 85000 Maroc',
    'PHONE': '0661-460593',
    'EMAIL': 'contact@resto-pecheur.ma',
    'WEBSITE': 'www.restopecheur.ma',
}