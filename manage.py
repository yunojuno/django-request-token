"""
This copy of manage.py explicitly sets the minimum settings required to be
able to manage migrations for the request_token app, and no more. It is not
designed to be used to run a site.

"""
import os
import sys

if __name__ == "__main__":

    from django.conf import settings
    from django.core.management import execute_from_command_line

    settings.configure(
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': os.getenv('DB_NAME', 'django_request_token'),
                'USER': os.getenv('DB_USER', 'postgres'),
                'PASSWORD': os.getenv('DB_PASSWORD', 'postgres'),
                'HOST': os.getenv('DB_HOST', 'localhost'),
                'PORT': os.getenv('DB_PORT', '5432'),
            }
        },
        INSTALLED_APPS = (
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'request_token',
        ),
        SECRET_KEY = 'django_request_token'
    )

    execute_from_command_line(sys.argv)
