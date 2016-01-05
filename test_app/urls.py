# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url

urlpatterns = patterns(
    'test_app.views',
    url(r'^decorated/$', 'decorated', name="decorated"),
    url(r'^undecorated/$', 'undecorated', name="undecorated"),
)
