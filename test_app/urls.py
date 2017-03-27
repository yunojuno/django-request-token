# -*- coding: utf-8 -*-
from django.conf.urls import url

from .views import decorated, undecorated

urlpatterns = [
    url(r'^decorated/$', decorated, name="decorated"),
    url(r'^undecorated/$', undecorated, name="undecorated"),
]
