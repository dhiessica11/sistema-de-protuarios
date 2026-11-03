"""Impressao digital interna versionada; nao representa assinatura eletronica."""

import hashlib
import json
from datetime import UTC

from .models import Registro

_CAMPOS_V1 = frozenset(
    {
        "id",
        "paciente",
        "autor",
        "categoria",
        "tipo",
        "origem",
        "justificativa",
        "contato_validacao",
        "resumo",
        "detalhe",
        "compartilhado",
        "criado_em",
    }
)


class RegistroNaoPersistido(ValueError):
    """A impressao digital exige registro previamente persistido."""


def impressao_digital_registro(registro_id):
    """Calcula SHA-256 do estado persistido; nao publica o conteudo clinico.

    Uso interno experimental. O formato final a assinar depende do provedor e da
    validacao juridica. Nao corresponde a PDF, comprovante ou assinatura gov.br.
    """
    if not registro_id:
        raise RegistroNaoPersistido("Registro persistido obrigatorio.")
    if {field.name for field in Registro._meta.concrete_fields} != _CAMPOS_V1:
        raise RuntimeError("Modelo de registro alterado; revisao da representacao necessaria.")
    registro = Registro.objects.get(pk=registro_id)
    instante = registro.criado_em
    if instante is None or instante.utcoffset() is None:
        raise ValueError("Data de criacao deve conter fuso horario.")
    payload = {
        "versao": "prontuario-registro-v1",
        "id": str(registro.pk),
        "paciente": str(registro.paciente_id),
        "autor": str(registro.autor_id),
        "categoria": registro.categoria,
        "tipo": registro.tipo,
        "origem": str(registro.origem_id) if registro.origem_id else None,
        "justificativa": registro.justificativa,
        "contato_validacao": registro.contato_validacao,
        "resumo": registro.resumo,
        "detalhe": registro.detalhe,
        "compartilhado": registro.compartilhado,
        "criado_em": instante.astimezone(UTC).isoformat(timespec="microseconds"),
    }
    representacao = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(representacao.encode("utf-8")).hexdigest()
