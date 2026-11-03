"""Permissoes de escrita por campo nos cadastros, independentes da categoria."""

from collections.abc import Mapping

from rest_framework.exceptions import PermissionDenied, ValidationError


def validar_campos_de_escrita(serializer, data):
    request = serializer.context.get("request")
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated or not user.is_active:
        raise PermissionDenied("Usuario autenticado e ativo obrigatorio.")
    if not isinstance(data, Mapping):
        return  # DRF produz o erro de formato do payload.

    if user.eh_admin:
        permitidos = (
            serializer.campos_criacao_admin
            if serializer.instance is None
            else serializer.campos_atualizacao_admin
        )
    elif user.eh_profissional_clinico and serializer.instance is not None:
        permitidos = serializer.campos_atualizacao_clinico
    else:
        raise PermissionDenied("Perfil sem permissao para esta operacao.")

    if not permitidos:
        raise PermissionDenied("Perfil sem permissao de escrita neste cadastro.")

    desconhecidos = set(data) - serializer.fields.keys()
    if desconhecidos:
        raise ValidationError({campo: "Campo desconhecido." for campo in sorted(desconhecidos)})
    proibidos = set(data) - permitidos
    if proibidos:
        raise PermissionDenied(
            {campo: "Sem permissao de escrita neste campo." for campo in sorted(proibidos)}
        )
