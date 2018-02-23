# -*- coding: utf-8 -*-
from django.urls import path

from .views import decorated, undecorated

app_name = 'test_app'

urlpatterns = [
    path(r'decorated/', decorated, name="decorated"),
    path(r'undecorated/', undecorated, name="undecorated"),
]
