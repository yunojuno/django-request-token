from distutils.version import StrictVersion
from os import getenv

import django

DJANGO_VERSION = StrictVersion(django.get_version())
assert DJANGO_VERSION >= StrictVersion("1.11")

DEBUG = True

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": getenv("TEST_DB_NAME", "test"),
        "USER": getenv("TEST_DB_USER", "postgres"),
        "PASSWORD": getenv("TEST_DB_PASSWORD", "postgres"),
        "HOST": getenv("TEST_DB_HOST", "localhost"),
        "PORT": getenv("TEST_DB_PORT", "5432"),
    }
}

INSTALLED_APPS = (
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.contenttypes",
    "request_token",
    "tests",
)

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "request_token.middleware.RequestTokenMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [
            # insert your TEMPLATE_DIRS here
        ],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "request_token.context_processors.request_token",
            ]
        },
    }
]

ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

SECRET_KEY = "request_token"

ROOT_URLCONF = "tests.urls"

APPEND_SLASH = True

STATIC_URL = "/static/"

TIME_ZONE = "UTC"

SITE_ID = 1

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s"
        },
        "simple": {"format": "%(levelname)s %(message)s"},
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "simple",
        }
    },
    "loggers": {"request_token": {"handlers": ["console"], "level": "DEBUG"}},
}

assert DEBUG is True, "This project is only intended to be used for testing."
