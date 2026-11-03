"""
Admin Django - APENAS para models operacionais.

ADR-005: Paciente, Responsavel, Consentimento, PacienteEquipe NAO sao registrados.
Esses passam pela UI propria com serializers DRF validando.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Clinica, Usuario


@admin.register(Usuario)
class UsuarioAdmin(DjangoUserAdmin):
    """Admin do usuario - mas sem expor campos cifrados (CPF, TOTP secret)."""

    list_display = ("username", "tipo", "first_name", "last_name", "is_active")
    list_filter = ("tipo", "is_active", "metodo_2fa")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("username",)

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("Pessoal", {"fields": ("first_name", "last_name", "email")}),
        ("Clinico", {"fields": ("tipo", "crfa", "crp", "crefito")}),
        (
            "Seguranca",
            {
                "fields": (
                    "metodo_2fa",
                    "yubikey_registrada",
                    "tentativas_falhas",
                    "conta_bloqueada",
                ),
            },
        ),
        (
            "Permissoes",
            {
                "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
            },
        ),
        ("Datas", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2", "tipo"),
            },
        ),
    )

    readonly_fields = ("last_login", "date_joined", "tentativas_falhas")


@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "criado_em")
    search_fields = ("nome", "cnpj")
    readonly_fields = ("id", "criado_em", "atualizado_em")


# INTENCIONALMENTE NAO REGISTRADO no Admin (ver ADR-005):
# - Paciente
# - Responsavel
# - Consentimento
# - PacienteEquipe
#
# Esses sao acessados exclusivamente pela UI propria do sistema,
# que valida regras CFFa 777 + LGPD via serializers DRF.
