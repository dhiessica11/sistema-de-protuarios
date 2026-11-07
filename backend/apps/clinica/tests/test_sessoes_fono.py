"""Registro de tentativas usa dados sintéticos e preserva isolamento clínico."""

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
from apps.clinica.models import SessaoFono, TipoUsuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def contexto(settings):
    settings.WEB_CONSULTA_HABILITADA = True
    paciente, fono = PacienteFactory(), FonoFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=fono)
    client = APIClient()
    client.force_authenticate(fono)
    return paciente, fono, client


def dados(paciente, **outros):
    return {
        "paciente": str(paciente.pk),
        "data": "2026-01-10",
        "atividade": "Brincadeira fictícia",
        "tentativas": ["I", "E", "G", "VP"],
        **outros,
    }


def item_plano(client, paciente):
    avaliacao = client.post(
        "/api/v1/avaliacoes-fono/",
        {
            "paciente": str(paciente.pk),
            "data": "2026-01-01",
            "protocolo": "Teste",
            "dificuldades_informadas": ["Dificuldade fictícia"],
        },
        format="json",
    ).data
    dificuldade = avaliacao["dificuldades"][0]["id"]
    revisao = client.post(
        f"/api/v1/dificuldades-fono/{dificuldade}/revisoes/",
        {"decisao": "aprovado", "texto": "Objetivo fictício"},
        format="json",
    ).data
    plano = client.post(
        "/api/v1/planos-fono/",
        {
            "paciente": str(paciente.pk),
            "inicio": "2026-01-01",
            "fim": "2026-06-01",
            "itens_informados": [{"revisao": revisao["id"], "meta": "Meta fictícia"}],
        },
        format="json",
    )
    assert plano.status_code == 201
    return plano.data["itens"][0]["id"]


def test_sessao_e_resultados(contexto):
    paciente, fono, client = contexto
    objetivo = item_plano(client, paciente)
    r = client.post("/api/v1/sessoes-fono/", dados(paciente, objetivo=objetivo), format="json")
    assert r.status_code == 201, r.data
    assert str(r.data["autor"]) == str(fono.pk)
    assert r.data["objetivo_texto"] == "Objetivo fictício"
    assert r.data["estado_assinatura"] == "sem_assinatura"
    assert r.data["resultados"]["tentativas"] == ["I", "E", "G", "VP"]
    assert r.data["resultados"]["total"] == 4
    assert r.data["resultados"]["percentual_independente"] == 25
    assert r.data["resultados"]["percentual_erro"] == 25
    assert r.data["resultados"]["percentual_ajuda"] == 50
    assert client.get("/api/v1/sessoes-fono/", {"paciente": str(paciente.pk)}).data["count"] == 1
    assert (
        client.patch(f"/api/v1/sessoes-fono/{r.data['id']}/", {}, format="json").status_code == 405
    )
    assert client.delete(f"/api/v1/sessoes-fono/{r.data['id']}/").status_code == 405


def test_sem_dados_e_validacoes(contexto):
    paciente, fono, client = contexto
    r = client.post("/api/v1/sessoes-fono/", dados(paciente, tentativas=[]), format="json")
    assert r.status_code == 201
    assert r.data["resultados"]["total"] == 0
    assert r.data["resultados"]["percentual_independente"] is None
    assert r.data["resultados"]["percentual_erro"] is None
    assert r.data["resultados"]["percentual_ajuda"] is None
    for invalido in [
        dados(paciente, tentativas=["X"]),
        dados(paciente, tentativas=["I"] * 101),
        dados(paciente, autor=str(fono.pk)),
        dados(paciente, resultados={}),
    ]:
        assert client.post("/api/v1/sessoes-fono/", invalido, format="json").status_code == 400
    assert client.get("/api/v1/sessoes-fono/", {"paciente": "inválido"}).status_code == 400


def test_privacidade_vinculo_e_texto_cifrado(contexto):
    paciente, fono, client = contexto
    client.post("/api/v1/sessoes-fono/", dados(paciente), format="json")
    for user in [TOFactory(), AdminFactory(), UsuarioFactory(tipo=TipoUsuario.TI), FonoFactory()]:
        c = APIClient()
        c.force_authenticate(user)
        response = c.get("/api/v1/sessoes-fono/", {"paciente": str(paciente.pk)})
        if user.tipo == TipoUsuario.FONO:
            assert response.status_code == 200 and response.data["count"] == 0
        else:
            assert response.status_code == 403
        assert c.post("/api/v1/sessoes-fono/", dados(paciente), format="json").status_code in (
            400,
            403,
        )
    with connection.cursor() as cursor:
        cursor.execute("SELECT atividade, tentativas_cifradas FROM clinica_sessaofono")
        atividade, tentativas = cursor.fetchone()
    assert "Brincadeira fictícia" not in atividade
    assert '"I"' not in tentativas
    outro = PacienteFactory()
    PacienteEquipeFactory(paciente=outro, profissional=fono)
    outro_item = item_plano(client, outro)
    assert (
        client.post(
            "/api/v1/sessoes-fono/", dados(paciente, objetivo=outro_item), format="json"
        ).status_code
        == 400
    )


def test_desabilitado_fora_de_desenvolvimento(contexto, settings):
    settings.WEB_CONSULTA_HABILITADA = False
    paciente, _, client = contexto
    assert client.get("/api/v1/sessoes-fono/", {"paciente": str(paciente.pk)}).status_code == 404


@pytest.mark.skipif(connection.vendor != "postgresql", reason="Trigger apenas em PostgreSQL")
def test_postgres_preserva_sessao_e_valida_objetivo(contexto):
    paciente, fono, client = contexto
    r = client.post("/api/v1/sessoes-fono/", dados(paciente), format="json")
    with pytest.raises(DatabaseError), transaction.atomic():
        SessaoFono.objects.filter(pk=r.data["id"]).update(atividade="alterada")
    with pytest.raises(DatabaseError), transaction.atomic():
        SessaoFono.objects.filter(pk=r.data["id"]).delete()
    outro = PacienteFactory()
    PacienteEquipeFactory(paciente=outro, profissional=fono)
    objetivo = item_plano(client, outro)
    with pytest.raises(DatabaseError), transaction.atomic():
        SessaoFono.objects.create(
            paciente=paciente,
            autor=fono,
            objetivo_id=objetivo,
            data="2026-01-10",
            atividade="X",
            tentativas_cifradas="[]",
        )
