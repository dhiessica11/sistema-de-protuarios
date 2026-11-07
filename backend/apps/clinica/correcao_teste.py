"""Garantias compartilhadas para correções aditivas de dados fictícios."""

from rest_framework.exceptions import ValidationError


def validar_paciente_correcao(attrs):
    anterior = attrs.get("corrige")
    if anterior and anterior.paciente_id != attrs["paciente"].id:
        raise ValidationError({"corrige": "A versão anterior deve pertencer ao mesmo paciente."})
    return attrs


def bloquear_e_validar_correcao(model, anterior):
    if anterior is None:
        return
    model.objects.select_for_update().get(pk=anterior.pk)
    if model.objects.filter(corrige_id=anterior.pk).exists():
        raise ValidationError(
            {"corrige": "Esta versão já possui uma correção; use a versão mais recente."}
        )
