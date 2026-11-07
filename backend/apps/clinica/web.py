"""Interface de consulta para validação em ambiente de desenvolvimento."""

from django.conf import settings
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


def habilitada():
    if not getattr(settings, "WEB_CONSULTA_HABILITADA", False):
        raise Http404


@never_cache
def entrar(request):
    habilitada()
    return auth_views.LoginView.as_view(
        template_name="clinica/entrar.html",
        redirect_authenticated_user=True,
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
        raise PermissionDenied
    return render(request, "clinica/inicio.html", {"clinico": request.user.eh_profissional_clinico})
