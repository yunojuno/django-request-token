# -*- coding: utf-8 -*-
from django.contrib import admin
from django.urls import include, path

admin.autodiscover()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('testing/', include('test_app.urls', namespace='testing')),
]
