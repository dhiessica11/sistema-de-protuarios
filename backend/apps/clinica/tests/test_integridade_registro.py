"""A impressao interna nao substitui assinatura e nao confia em objeto do cliente."""

from copy import copy
from datetime import timedelta
from uuid import uuid4

import pytest
from django.db import connection

from apps.clinica import integridade_registro
from apps.clinica.factories import FonoFactory, PacienteEquipeFactory, PacienteFactory
from apps.clinica.integridade_registro import RegistroNaoPersistido, impressao_digital_registro
from apps.clinica.models import Registro

pytestmark = pytest.mark.django_db


@pytest.fixture
def registro():
    paciente = PacienteFactory()
    autor = FonoFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=autor)
    return Registro.objects.create(
        paciente=paciente, autor=autor, categoria=autor.tipo, detalhe="Conteudo clinico sintetico"
    )


def test_hash_estavel_e_sem_conteudo_em_texto_claro(registro):
    primeiro = impressao_digital_registro(registro.pk)
    segundo = impressao_digital_registro(registro.pk)
    assert primeiro == segundo
    assert len(primeiro) == 64
    assert "Conteudo" not in primeiro


def test_alteracoes_em_memoria_nao_afetam_estado_persistido(registro):
    antes = impressao_digital_registro(registro.pk)
    registro.detalhe = "Alteracao nao salva"
    assert impressao_digital_registro(registro.pk) == antes


def test_novo_registro_possui_identidade_diferente(registro):
    outro = Registro.objects.create(
        paciente=registro.paciente,
        autor=registro.autor,
        categoria=registro.categoria,
        detalhe=registro.detalhe,
    )
    assert impressao_digital_registro(outro.pk) != impressao_digital_registro(registro.pk)


def test_registro_nao_persistido_e_rejeitado():
    with pytest.raises(RegistroNaoPersistido):
        impressao_digital_registro(None)


def test_mudanca_de_esquema_exige_revisao(registro, monkeypatch):
    monkeypatch.setattr(integridade_registro, "_CAMPOS_V1", frozenset({"id"}))
    with pytest.raises(RuntimeError, match="revisao"):
        impressao_digital_registro(registro.pk)


@pytest.mark.parametrize(
    "campo,valor",
    [
        ("id", uuid4()),
        ("paciente_id", uuid4()),
        ("autor_id", uuid4()),
        ("categoria", "to"),
        ("tipo", "adendo"),
        ("origem_id", uuid4()),
        ("justificativa", "novo motivo"),
        ("contato_validacao", "pessoa consultada"),
        ("resumo", "novo resumo"),
        ("detalhe", "novo detalhe"),
        ("compartilhado", True),
        ("criado_em", "alterar_data"),
    ],
)
def test_cada_campo_afeta_impressao_digital(registro, monkeypatch, campo, valor):
    original = impressao_digital_registro(registro.pk)
    alterado = copy(registro)
    if campo == "criado_em":
        valor = registro.criado_em + timedelta(seconds=1)
    setattr(alterado, campo, valor)
    monkeypatch.setattr(Registro.objects, "get", lambda **kwargs: alterado)
    assert impressao_digital_registro(registro.pk) != original


def test_dados_clinicos_nao_sao_gravados_em_claro(registro):
    with connection.cursor() as cursor:
        cursor.execute("SELECT detalhe FROM clinica_registro WHERE id = %s", [registro.pk.hex])
        valor = cursor.fetchone()[0]
    assert "Conteudo clinico sintetico" not in valor
