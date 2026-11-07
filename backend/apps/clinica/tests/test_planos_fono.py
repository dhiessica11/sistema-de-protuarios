"""Planos de teste mantêm objetivos aprovados e sua origem."""

import pytest
from django.db import DatabaseError, connection, transaction
from rest_framework.test import APIClient

from apps.clinica.factories import (
    AdminFactory,
    FonoFactory,
    PacienteEquipeFactory,
    PacienteFactory,
    TOFactory,
)
from apps.clinica.models import ItemPlanoFono, PlanoFono

pytestmark = pytest.mark.django_db


@pytest.fixture
def contexto(settings):
    settings.WEB_CONSULTA_HABILITADA = True
    paciente, fono = PacienteFactory(), FonoFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=fono)
    client = APIClient()
    client.force_authenticate(fono)
    avaliacao = client.post(
        "/api/v1/avaliacoes-fono/",
        {
            "paciente": str(paciente.pk),
            "data": "2026-01-01",
            "protocolo": "Ficha teste",
            "dificuldades_informadas": ["Dificuldade de teste"],
        },
        format="json",
    ).data
    dificuldade = avaliacao["dificuldades"][0]["id"]
    aprovada = client.post(
        f"/api/v1/dificuldades-fono/{dificuldade}/revisoes/",
        {"decisao": "aprovado", "texto": "Objetivo aprovado"},
        format="json",
    ).data
    return paciente, fono, client, dificuldade, aprovada


def payload(paciente, revisao, **kwargs):
    return {
        "paciente": str(paciente.pk),
        "inicio": "2026-01-01",
        "fim": "2026-06-01",
        "recursos": "Recursos fictícios",
        "itens_informados": [{"revisao": revisao, "meta": "Meta fictícia"}],
        **kwargs,
    }


def test_plano_preserva_revisao_historica(contexto):
    paciente, fono, client, dificuldade, aprovada = contexto
    r = client.post("/api/v1/planos-fono/", payload(paciente, aprovada["id"]), format="json")
    assert r.status_code == 201, r.data
    assert str(r.data["autor"]) == str(fono.pk)
    assert r.data["estado_assinatura"] == "sem_assinatura"
    assert r.data["itens"][0]["objetivo"] == "Objetivo aprovado"
    assert r.data["itens"][0]["dificuldade"] == "Dificuldade de teste"
    client.post(
        f"/api/v1/dificuldades-fono/{dificuldade}/revisoes/",
        {"decisao": "descartado", "texto": "Não usar"},
        format="json",
    )
    assert (
        client.post(
            "/api/v1/planos-fono/", payload(paciente, aprovada["id"]), format="json"
        ).status_code
        == 400
    )
    historico = client.get("/api/v1/planos-fono/", {"paciente": str(paciente.pk)})
    assert historico.data["results"][0]["itens"][0]["objetivo"] == "Objetivo aprovado"
    assert (
        client.patch(f"/api/v1/planos-fono/{r.data['id']}/", {}, format="json").status_code == 405
    )
    assert client.delete(f"/api/v1/planos-fono/{r.data['id']}/").status_code == 405


def test_sem_acesso_ou_revisao_de_outro_paciente(contexto):
    paciente, fono, client, _, aprovada = contexto
    outro = PacienteFactory()
    PacienteEquipeFactory(paciente=outro, profissional=fono)
    assert (
        client.post(
            "/api/v1/planos-fono/", payload(outro, aprovada["id"]), format="json"
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/planos-fono/",
            payload(paciente, aprovada["id"], autor=str(fono.pk)),
            format="json",
        ).status_code
        == 400
    )
    for user in [TOFactory(), AdminFactory(), FonoFactory()]:
        c = APIClient()
        c.force_authenticate(user)
        r = c.get("/api/v1/planos-fono/", {"paciente": str(paciente.pk)})
        if user.tipo != "fono":
            assert r.status_code == 403
        else:
            assert r.data["count"] == 0
        assert c.post(
            "/api/v1/planos-fono/", payload(paciente, aprovada["id"]), format="json"
        ).status_code in (400, 403)


def test_validacoes_e_cifra(contexto):
    paciente, _, client, _, aprovada = contexto
    assert (
        client.post(
            "/api/v1/planos-fono/",
            payload(paciente, aprovada["id"], fim="2025-01-01"),
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/planos-fono/",
            payload(paciente, aprovada["id"], itens_informados=[]),
            format="json",
        ).status_code
        == 400
    )
    item = {"revisao": aprovada["id"], "meta": "Meta fictícia"}
    assert (
        client.post(
            "/api/v1/planos-fono/",
            payload(paciente, aprovada["id"], itens_informados=[item, item]),
            format="json",
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/planos-fono/", payload(paciente, aprovada["id"]), format="json"
        ).status_code
        == 201
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT meta FROM clinica_itemplanofono")
        assert "Meta fictícia" not in cursor.fetchone()[0]


def test_desabilitado_fora_de_desenvolvimento(contexto, settings):
    settings.WEB_CONSULTA_HABILITADA = False
    paciente, _, client, _, _ = contexto
    assert client.get("/api/v1/planos-fono/", {"paciente": str(paciente.pk)}).status_code == 404


@pytest.mark.skipif(connection.vendor != "postgresql", reason="Triggers apenas em PostgreSQL")
def test_postgres_preserva_planos(contexto):
    paciente, _, client, _, aprovada = contexto
    plano = client.post(
        "/api/v1/planos-fono/", payload(paciente, aprovada["id"]), format="json"
    ).data
    operacoes = [
        lambda: PlanoFono.objects.filter(pk=plano["id"]).update(recursos="alterado"),
        lambda: ItemPlanoFono.objects.filter(plano_id=plano["id"]).delete(),
    ]
    for operacao in operacoes:
        with pytest.raises(DatabaseError), transaction.atomic():
            operacao()


@pytest.mark.skipif(connection.vendor != "postgresql", reason="Triggers apenas em PostgreSQL")
def test_postgres_rejeita_revisao_de_outro_paciente(contexto):
    paciente, fono, client, _, aprovada = contexto
    plano = client.post(
        "/api/v1/planos-fono/", payload(paciente, aprovada["id"]), format="json"
    ).data
    outro = PacienteFactory()
    PacienteEquipeFactory(paciente=outro, profissional=fono)
    avaliacao = client.post(
        "/api/v1/avaliacoes-fono/",
        {
            "paciente": str(outro.pk),
            "data": "2026-01-01",
            "protocolo": "Outro",
            "dificuldades_informadas": ["Outra dificuldade"],
        },
        format="json",
    ).data
    revisao = client.post(
        f"/api/v1/dificuldades-fono/{avaliacao['dificuldades'][0]['id']}/revisoes/",
        {"decisao": "aprovado", "texto": "Outro objetivo"},
        format="json",
    ).data
    with pytest.raises(DatabaseError), transaction.atomic():
        ItemPlanoFono.objects.create(plano_id=plano["id"], revisao_id=revisao["id"], meta="Meta")
