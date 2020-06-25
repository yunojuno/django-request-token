from django.conf import settings
from django.urls import path
from django.contrib import admin
from .views import decorated, roundtrip, undecorated
from django.conf.urls.static import static

app_name = "tests"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("decorated/$", decorated, name="decorated"),
    path("roundtrip/", roundtrip, name="roundtrip"),
    path("undecorated/", undecorated, name="undecorated"),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)