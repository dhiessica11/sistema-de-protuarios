"""Retificacoes e adendos criam registros novos, sem alterar o original."""

import pytest
from rest_framework.test import APIClient

from apps.clinica.factories import FonoFactory, PacienteEquipeFactory, PacienteFactory, TOFactory
from apps.clinica.models import Registro, TipoRegistro

pytestmark = pytest.mark.django_db


@pytest.fixture
def contexto():
    paciente = PacienteFactory()
    profissional = FonoFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=profissional)
    original = Registro.objects.create(
        paciente=paciente, autor=profissional, categoria=profissional.tipo, detalhe="Texto original"
    )
    client = APIClient()
    client.force_authenticate(profissional)
    return paciente, profissional, original, client


def payload(paciente, original, tipo):
    return {
        "paciente": str(paciente.pk),
        "origem": str(original.pk),
        "tipo": tipo,
        "detalhe": "Texto posterior",
        "justificativa": "Motivo documental e profissional da correcao, com contato efetuado.",
        "contato_validacao": "Profissional consultado",
    }


def test_retificacao_e_retificacao_de_retificacao_preservam_original(contexto):
    from django.db import connection

    paciente, profissional, original, client = contexto
    response = client.post(
        "/api/v1/registros/", payload(paciente, original, "retificacao"), format="json"
    )
    assert response.status_code == 201, response.data
    assert response.data["estado_assinatura"] == "sem_assinatura"
    nova = Registro.objects.get(pk=response.data["id"])
    assert nova.origem_id == original.pk and nova.tipo == TipoRegistro.RETIFICACAO
    assert nova.autor_id == profissional.pk and nova.categoria == profissional.tipo
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT justificativa, contato_validacao FROM clinica_registro WHERE id = %s",
            [nova.pk.hex],
        )
        motivo_cifrado, contato_cifrado = cursor.fetchone()
    assert "Motivo documental" not in motivo_cifrado
    assert "Profissional consultado" not in contato_cifrado
    original.refresh_from_db()
    assert original.detalhe == "Texto original"
    response = client.post(
        "/api/v1/registros/", payload(paciente, nova, "retificacao"), format="json"
    )
    assert response.status_code == 201
    assert Registro.objects.get(pk=response.data["id"]).origem_id == nova.pk
    assert Registro.objects.count() == 3


def test_adendo_sem_justificativa_preserva_original(contexto):
    paciente, _, original, client = contexto
    dados = payload(paciente, original, "adendo")
    dados.pop("justificativa")
    dados.pop("contato_validacao")
    response = client.post("/api/v1/registros/", dados, format="json")
    assert response.status_code == 201, response.data
    novo = Registro.objects.get(pk=response.data["id"])
    assert novo.origem_id == original.pk and novo.tipo == TipoRegistro.ADENDO
    assert novo.justificativa == ""
    original.refresh_from_db()
    assert original.detalhe == "Texto original"


def test_outro_profissional_da_mesma_categoria_assume_autoria_da_retificacao(contexto):
    paciente, autor_original, original, _ = contexto
    outro = FonoFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=outro)
    client = APIClient()
    client.force_authenticate(outro)
    response = client.post(
        "/api/v1/registros/", payload(paciente, original, "retificacao"), format="json"
    )
    assert response.status_code == 201
    retificacao = Registro.objects.get(pk=response.data["id"])
    assert retificacao.autor_id == outro.pk
    assert retificacao.categoria == original.categoria
    original.refresh_from_db()
    assert original.autor_id == autor_original.pk


@pytest.mark.parametrize("motivo", ["", "curto", " " * 60])
def test_retificacao_exige_justificativa(contexto, motivo):
    paciente, _, original, client = contexto
    response = client.post(
        "/api/v1/registros/",
        {**payload(paciente, original, "retificacao"), "justificativa": motivo},
        format="json",
    )
    assert response.status_code == 400
    assert "justificativa" in response.data
    assert Registro.objects.count() == 1


@pytest.mark.parametrize("contato", [None, "", "   "])
def test_retificacao_exige_contato_de_validacao(contexto, contato):
    paciente, _, original, client = contexto
    dados = payload(paciente, original, "retificacao")
    if contato is None:
        dados.pop("contato_validacao")
    else:
        dados["contato_validacao"] = contato
    response = client.post("/api/v1/registros/", dados, format="json")
    assert response.status_code == 400
    assert "contato_validacao" in response.data
    assert Registro.objects.count() == 1


def test_nao_aceita_origem_de_outro_paciente(contexto):
    paciente, profissional, _, client = contexto
    outro = PacienteFactory(clinica=paciente.clinica)
    PacienteEquipeFactory(paciente=outro, profissional=profissional)
    origem = Registro.objects.create(
        paciente=outro, autor=profissional, categoria=profissional.tipo, detalhe="Original"
    )
    response = client.post(
        "/api/v1/registros/", payload(paciente, origem, "retificacao"), format="json"
    )
    assert response.status_code == 400
    assert Registro.objects.count() == 2


@pytest.mark.parametrize("tipo", ["retificacao", "adendo"])
@pytest.mark.parametrize("compartilhado", [False, True])
def test_outra_categoria_nao_pode_derivar(contexto, tipo, compartilhado):
    paciente, autor, original, _ = contexto
    if compartilhado:
        original = Registro.objects.create(
            paciente=paciente,
            autor=autor,
            categoria=autor.tipo,
            detalhe="Original compartilhado",
            compartilhado=True,
        )
    total = Registro.objects.count()
    to = TOFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=to)
    client = APIClient()
    client.force_authenticate(to)
    response = client.post("/api/v1/registros/", payload(paciente, original, tipo), format="json")
    assert response.status_code == 400
    assert Registro.objects.count() == total


def test_origem_obrigatoria_e_estado_de_assinatura_nao_forjavel(contexto):
    paciente, _, original, client = contexto
    dados = payload(paciente, original, "retificacao")
    dados.pop("origem")
    assert client.post("/api/v1/registros/", dados, format="json").status_code == 400
    dados = {**payload(paciente, original, "retificacao"), "assinado": True}
    assert client.post("/api/v1/registros/", dados, format="json").status_code == 400
    dados = {**payload(paciente, original, "retificacao"), "estado_assinatura": "assinado"}
    assert client.post("/api/v1/registros/", dados, format="json").status_code == 400
    assert Registro.objects.count() == 1


def test_compartilhamento_nao_expoe_origem_ou_justificativa(contexto):
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    paciente, _, original, client = contexto
    dados = {
        **payload(paciente, original, "retificacao"),
        "compartilhado": True,
        "resumo": "Resumo partilhado",
    }
    response = client.post("/api/v1/registros/", dados, format="json")
    assert response.status_code == 201
    to = TOFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=to)
    outro = APIClient()
    outro.force_authenticate(to)
    with CaptureQueriesContext(connection) as queries:
        visto = outro.get(f"/api/v1/registros/{response.data['id']}/")
    assert visto.status_code == 200
    assert visto.data["resumo"] == "Resumo partilhado"
    assert visto.data["estado_assinatura"] == "sem_assinatura"
    assert "detalhe" not in visto.data
    assert "origem" not in visto.data
    assert "justificativa" not in visto.data
    assert "contato_validacao" not in visto.data
    consultas = [q["sql"] for q in queries.captured_queries if "clinica_registro" in q["sql"]]
    assert consultas
    for consulta in consultas:
        assert '"clinica_registro"."detalhe"' not in consulta
        assert '"clinica_registro"."justificativa"' not in consulta
        assert '"clinica_registro"."contato_validacao"' not in consulta
    assert outro.get(f"/api/v1/registros/{original.pk}/").status_code == 404


def test_evolucao_nao_pode_apontar_para_original(contexto):
    paciente, _, original, client = contexto
    dados = payload(paciente, original, "evolucao")
    response = client.post("/api/v1/registros/", dados, format="json")
    assert response.status_code == 400
    assert Registro.objects.count() == 1


def test_constraints_bloqueiam_retificacao_inconsistente_no_banco(contexto):
    from django.db import IntegrityError, transaction

    paciente, profissional, original, _ = contexto
    with pytest.raises(IntegrityError), transaction.atomic():
        Registro.objects.create(
            paciente=paciente,
            autor=profissional,
            categoria=profissional.tipo,
            tipo="retificacao",
            detalhe="Texto",
            justificativa="a" * 50,
            contato_validacao="Profissional consultado",
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Registro.objects.create(
            paciente=paciente,
            autor=profissional,
            categoria=profissional.tipo,
            tipo="retificacao",
            origem=original,
            detalhe="Texto",
            contato_validacao="Profissional consultado",
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        Registro.objects.create(
            paciente=paciente,
            autor=profissional,
            categoria=profissional.tipo,
            tipo="retificacao",
            origem=original,
            detalhe="Texto",
            justificativa="a" * 50,
        )
    assert Registro.objects.count() == 1


def test_banco_bloqueia_origem_de_outra_categoria_ou_paciente(contexto):
    from django.db import DatabaseError, connection, transaction

    if connection.vendor != "postgresql":
        pytest.skip("Exige PostgreSQL")
    paciente, profissional, original, _ = contexto
    to = TOFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=to)
    outro = PacienteFactory(clinica=paciente.clinica)
    PacienteEquipeFactory(paciente=outro, profissional=profissional)
    casos = [(paciente, to), (outro, profissional)]
    for alvo, autor in casos:
        with pytest.raises(DatabaseError, match="Origem deve pertencer"), transaction.atomic():
            Registro.objects.create(
                paciente=alvo,
                autor=autor,
                categoria=autor.tipo,
                tipo="retificacao",
                origem=original,
                detalhe="Texto",
                justificativa="a" * 50,
                contato_validacao="Profissional consultado",
            )
    assert Registro.objects.count() == 1
