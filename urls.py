# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url, include
from django.contrib import admin  # , staticfiles

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^testing/', include('test_app.urls', namespace="testing")),
)
