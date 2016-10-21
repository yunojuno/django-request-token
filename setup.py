# -*- coding: utf-8 -*-
"""request_token package setup."""
import os
from setuptools import setup, find_packages

README = open(os.path.join(os.path.dirname(__file__), 'README.rst')).read()

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

setup(
    name="django-request-token",
    version="0.2.0",
    packages=find_packages(),
    install_requires=['Django>=1.8', 'pyjwt'],
    include_package_data=True,
    description='JWT-backed Django app for managing querystring tokens.',
    long_description=README,
    url='https://github.com/yunojuno/django-request-token',
    author='Hugo Rodger-Brown',
    author_email='hugo@yunojuno.com',
    maintainer='Hugo Rodger-Brown',
    maintainer_email='hugo@yunojuno.com',
    classifiers=[
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
    ],
)
