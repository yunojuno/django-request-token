try:
    from django.urls import re_path
except ImportError:
    from django.conf.urls import url as re_path

from .views import decorated, undecorated, roundtrip

app_name = "tests"

urlpatterns = [
    re_path(r"^decorated/$", decorated, name="decorated"),
    re_path(r"^roundtrip/$", roundtrip, name="roundtrip"),
    re_path(r"^undecorated/$", undecorated, name="undecorated"),
]
