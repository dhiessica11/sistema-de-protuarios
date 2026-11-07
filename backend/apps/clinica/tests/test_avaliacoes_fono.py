"""Fluxo sintético, sem regras clínicas de protocolos."""

import pytest
from django.db import DatabaseError, connection, transaction
from rest_framework.test import APIClient

from apps.clinica.factories import (
    AdminFactory,
    FonoFactory,
    PacienteEquipeFactory,
    PacienteFactory,
    TOFactory,
    UsuarioFactory,
)
from apps.clinica.models import AvaliacaoFono, DificuldadeFono, TipoUsuario

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def habilitar_interface(settings):
    settings.WEB_CONSULTA_HABILITADA = True


@pytest.fixture
def contexto():
    paciente = PacienteFactory()
    fono = FonoFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=fono)
    client = APIClient()
    client.force_authenticate(fono)
    return paciente, fono, client


def payload(paciente, **kwargs):
    return {
        "paciente": str(paciente.pk),
        "data": "2026-01-10",
        "protocolo": "Ficha teste",
        "dificuldades_informadas": ["Dificuldade A", "Dificuldade B"],
        **kwargs,
    }


def test_avaliacao_revisao_e_reavaliacao(contexto):
    paciente, fono, client = contexto
    resposta = client.post("/api/v1/avaliacoes-fono/", payload(paciente), format="json")
    assert resposta.status_code == 201, resposta.data
    assert str(resposta.data["autor"]) == str(fono.pk)
    dificuldades = resposta.data["dificuldades"]
    assert len(dificuldades) == 2
    assert dificuldades[0]["descricao"] in dificuldades[0]["proposta"]
    assert dificuldades[0]["revisoes"] == []
    dificuldade = dificuldades[0]["id"]
    revisao = client.post(
        f"/api/v1/dificuldades-fono/{dificuldade}/revisoes/",
        {"decisao": "aprovado", "texto": "Objetivo revisado"},
        format="json",
    )
    assert revisao.status_code == 201
    assert str(revisao.data["autor"]) == str(fono.pk)
    resposta2 = client.post(
        "/api/v1/avaliacoes-fono/",
        payload(
            paciente, data="2026-02-10", origem=resposta.data["id"], dificuldades_informadas=[]
        ),
        format="json",
    )
    assert resposta2.status_code == 201
    historico = client.get("/api/v1/avaliacoes-fono/", {"paciente": str(paciente.pk)})
    assert historico.data["count"] == 2
    anterior = next(item for item in historico.data["results"] if item["id"] == resposta.data["id"])
    assert anterior["dificuldades"][0]["revisoes"][0]["texto"] == "Objetivo revisado"
    assert (
        client.patch(
            f"/api/v1/avaliacoes-fono/{resposta.data['id']}/", {}, format="json"
        ).status_code
        == 405
    )
    assert client.delete(f"/api/v1/avaliacoes-fono/{resposta.data['id']}/").status_code == 405


def test_acesso_e_autoria(contexto):
    paciente, fono, client = contexto
    resposta = client.post("/api/v1/avaliacoes-fono/", payload(paciente), format="json")
    dificuldade = resposta.data["dificuldades"][0]["id"]
    assert (
        client.post(
            "/api/v1/avaliacoes-fono/", payload(paciente, autor=str(fono.pk)), format="json"
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/dificuldades-fono/{dificuldade}/revisoes/",
            {"autor": str(fono.pk), "decisao": "aprovado", "texto": "teste"},
            format="json",
        ).status_code
        == 400
    )
    for user in [TOFactory(), AdminFactory(), UsuarioFactory(tipo=TipoUsuario.TI)]:
        PacienteEquipeFactory(paciente=paciente, profissional=user)
        c = APIClient()
        c.force_authenticate(user)
        assert c.get("/api/v1/avaliacoes-fono/", {"paciente": str(paciente.pk)}).status_code == 403
        assert (
            c.post(
                f"/api/v1/dificuldades-fono/{dificuldade}/revisoes/",
                {"decisao": "aprovado", "texto": "teste"},
                format="json",
            ).status_code
            == 403
        )
    outro = FonoFactory()
    c = APIClient()
    c.force_authenticate(outro)
    assert c.get("/api/v1/avaliacoes-fono/", {"paciente": str(paciente.pk)}).data["count"] == 0
    assert (
        c.post(
            f"/api/v1/dificuldades-fono/{dificuldade}/revisoes/",
            {"decisao": "aprovado", "texto": "teste"},
            format="json",
        ).status_code
        == 404
    )
    assert c.post("/api/v1/avaliacoes-fono/", payload(paciente), format="json").status_code == 400


def test_origem_e_dados_invalidos(contexto):
    paciente, _, client = contexto
    avaliacao = client.post("/api/v1/avaliacoes-fono/", payload(paciente), format="json").data
    assert (
        client.post(
            "/api/v1/avaliacoes-fono/",
            payload(paciente, origem=avaliacao["id"], data="2026-01-01"),
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/avaliacoes-fono/",
            payload(paciente, origem=avaliacao["id"], protocolo="Outro protocolo"),
            format="json",
        ).status_code
        == 400
    )
    outro = PacienteFactory()
    PacienteEquipeFactory(paciente=outro, profissional=contexto[1])
    assert (
        client.post(
            "/api/v1/avaliacoes-fono/", payload(outro, origem=avaliacao["id"]), format="json"
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/avaliacoes-fono/",
            payload(paciente, dificuldades_informadas=["  "]),
            format="json",
        ).status_code
        == 400
    )
    assert client.get("/api/v1/avaliacoes-fono/", {"paciente": "inválido"}).status_code == 400


def test_texto_cifrado(contexto):
    paciente, _, client = contexto
    client.post("/api/v1/avaliacoes-fono/", payload(paciente), format="json")
    with connection.cursor() as cursor:
        cursor.execute("SELECT descricao, proposta FROM clinica_dificuldadefono")
        descricao, proposta = cursor.fetchone()
    assert "Dificuldade A" not in descricao
    assert "Dificuldade A" not in proposta


def test_desabilitado_fora_de_desenvolvimento(contexto, settings):
    settings.WEB_CONSULTA_HABILITADA = False
    paciente, _, client = contexto
    assert client.get("/api/v1/avaliacoes-fono/", {"paciente": str(paciente.pk)}).status_code == 404


@pytest.mark.skipif(connection.vendor != "postgresql", reason="Triggers apenas em PostgreSQL")
def test_postgres_impede_alteracao_e_exclusao(contexto):
    paciente, _, client = contexto
    r = client.post("/api/v1/avaliacoes-fono/", payload(paciente), format="json")
    dificuldade = r.data["dificuldades"][0]["id"]
    for operacao in [
        lambda: AvaliacaoFono.objects.filter(pk=r.data["id"]).update(protocolo="modificado"),
        lambda: DificuldadeFono.objects.filter(pk=dificuldade).delete(),
    ]:
        with pytest.raises(DatabaseError), transaction.atomic():
            operacao()
