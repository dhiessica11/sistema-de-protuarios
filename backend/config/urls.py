from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path

from apps.clinica import web


def health(_request):
    return JsonResponse({"status": "ok", "service": "prontuario-ed"})


urlpatterns = [
    path("", web.inicio, name="web-inicio"),
    path("entrar/", web.entrar, name="web-entrar"),
    path("sair/", web.sair, name="web-sair"),
    path("admin/", admin.site.urls),
    path("health/", health, name="health"),
    path("api/v1/", include("apps.clinica.urls")),
    path("api/auth/", include("rest_framework.urls")),  # login browsable
]
