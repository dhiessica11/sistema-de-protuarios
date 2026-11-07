"""Interface de consulta para validação em ambiente de desenvolvimento."""

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from .permissions import admin_clinico_teste


def habilitada():
    if not getattr(settings, "WEB_CONSULTA_HABILITADA", False):
        raise Http404


@never_cache
def entrar(request):
    habilitada()
    return auth_views.LoginView.as_view(
        template_name="clinica/entrar.html",
        redirect_authenticated_user=False,
        next_page="web-inicio",
    )(request)


@never_cache
def sair(request):
    habilitada()
    return auth_views.LogoutView.as_view(next_page="web-entrar")(request)


@never_cache
@require_GET
@login_required(login_url="web-entrar")
def inicio(request):
    habilitada()
    if not (request.user.eh_admin or request.user.eh_profissional_clinico):
        return render(request, "clinica/acesso_restrito.html", status=403)
    return render(
        request,
        "clinica/inicio.html",
        {
            "clinico": request.user.eh_profissional_clinico or admin_clinico_teste(request.user),
            "fono": request.user.tipo == "fono" or admin_clinico_teste(request.user),
            "admin_teste": admin_clinico_teste(request.user),
        },
    )
