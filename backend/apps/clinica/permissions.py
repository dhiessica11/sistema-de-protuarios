"""
Permissoes de autorizacao da API.

Separadas das views pra facilitar teste e revisao independente.
"""

from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    """Usuario tipo admin ou TI."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, "eh_admin", False)


class IsProfissionalClinico(BasePermission):
    """Usuario tipo fono, TO ou psico."""

    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(
            request.user, "eh_profissional_clinico", False
        )


class IsAdminOrClinico(BasePermission):
    """Admin OU profissional clinico (autenticado)."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return getattr(request.user, "eh_admin", False) or getattr(
            request.user, "eh_profissional_clinico", False
        )


class PacienteNoScopeDoProfissional(BasePermission):
    """
    Object-level: profissional so acessa paciente onde esta em
    PacienteEquipe ativo. Admin acessa tudo.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user.is_authenticated:
            return False
        if getattr(user, "eh_admin", False):
            return True
        if getattr(user, "eh_profissional_clinico", False):
            paciente = _extrair_paciente(obj)
            if paciente is None:
                return False
            return paciente.equipe.filter(profissional=user, ativo=True).exists()
        return False


def _extrair_paciente(obj):
    """Resolve o Paciente associado a diferentes models."""
    from .models import Paciente

    if isinstance(obj, Paciente):
        return obj
    return getattr(obj, "paciente", None)
