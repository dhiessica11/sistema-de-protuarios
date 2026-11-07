"""Evolução descritiva por objetivo, com isolamento e denominadores corretos."""

import pytest
from rest_framework.test import APIClient

from apps.clinica.factories import (
    AdminFactory,
    FonoFactory,
    PacienteEquipeFactory,
    PacienteFactory,
    TOFactory,
)
from apps.clinica.tests.test_sessoes_fono import dados, item_plano

pytestmark = pytest.mark.django_db


@pytest.fixture
def contexto(settings):
    settings.WEB_CONSULTA_HABILITADA = True
    paciente, fono = PacienteFactory(), FonoFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=fono)
    client = APIClient()
    client.force_authenticate(fono)
    objetivo = item_plano(client, paciente)
    return paciente, fono, client, objetivo


def query(paciente, objetivo, **kwargs):
    return {
        "paciente": str(paciente.pk),
        "objetivo": objetivo,
        "inicio": "2026-01-01",
        "fim": "2026-02-28",
        **kwargs,
    }


def test_percentuais_ponderados_por_tentativa_e_sem_dados(contexto):
    paciente, _, client, objetivo = contexto
    for data, tentativas in [
        ("2026-01-10", ["I"]),
        ("2026-01-10", ["E", "E", "G"]),
        ("2026-01-11", []),
    ]:
        assert (
            client.post(
                "/api/v1/sessoes-fono/",
                dados(paciente, data=data, objetivo=objetivo, tentativas=tentativas),
                format="json",
            ).status_code
            == 201
        )
    r = client.get("/api/v1/sessoes-fono/evolucao/", query(paciente, objetivo))
    assert r.status_code == 200
    assert "no-store" in r["Cache-Control"]
    primeiro, segundo = r.data["pontos"]
    assert primeiro["data"] == "2026-01-10"
    assert primeiro["sessoes"] == 2 and primeiro["total"] == 4
    assert primeiro["percentual_independentes"] == 25
    assert primeiro["percentual_erros"] == 50
    assert primeiro["percentual_ajudas"] == 25
    assert segundo["total"] == 0 and segundo["sessoes"] == 1
    assert segundo["percentual_independentes"] is None
    assert segundo["percentual_erros"] is None
    assert segundo["percentual_ajudas"] is None
    assert (
        client.get(
            "/api/v1/sessoes-fono/evolucao/", query(paciente, objetivo, inicio="2026-01-12")
        ).data["pontos"]
        == []
    )


def test_filtros_e_privacidade(contexto):
    paciente, fono, client, objetivo = contexto
    url = "/api/v1/sessoes-fono/evolucao/"
    assert client.get(url, query(paciente, objetivo, inicio="inválido")).status_code == 400
    assert client.get(url, query(paciente, objetivo, fim="2028-02-01")).status_code == 400
    assert client.get(url, query(paciente, objetivo, fim="2025-12-31")).status_code == 400
    assert client.get(url, query(paciente, "inválido")).status_code == 400
    outro = PacienteFactory()
    PacienteEquipeFactory(paciente=outro, profissional=fono)
    assert client.get(url, query(outro, objetivo)).status_code == 404
    for user in [TOFactory(), AdminFactory(), FonoFactory()]:
        c = APIClient()
        c.force_authenticate(user)
        response = c.get(url, query(paciente, objetivo))
        assert response.status_code == (404 if user.tipo == "fono" else 403)


def test_objetivos_diferentes_nao_sao_misturados(contexto):
    paciente, _, client, objetivo = contexto
    outro = item_plano(client, paciente)
    client.post(
        "/api/v1/sessoes-fono/", dados(paciente, objetivo=objetivo, tentativas=["I"]), format="json"
    )
    client.post(
        "/api/v1/sessoes-fono/",
        dados(paciente, objetivo=outro, tentativas=["E", "E"]),
        format="json",
    )
    r = client.get("/api/v1/sessoes-fono/evolucao/", query(paciente, objetivo))
    assert r.data["pontos"][0]["total"] == 1
    assert r.data["pontos"][0]["percentual_independentes"] == 100


def test_desabilitado_em_outros_ambientes(contexto, settings):
    settings.WEB_CONSULTA_HABILITADA = False
    paciente, _, client, objetivo = contexto
    assert (
        client.get("/api/v1/sessoes-fono/evolucao/", query(paciente, objetivo)).status_code == 404
    )
