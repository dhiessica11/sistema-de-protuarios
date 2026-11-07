"""Admin só tem acesso clínico amplo na configuração explícita de dados fictícios."""

import pytest
from django.db import DatabaseError, connection, transaction
from django.test import Client, override_settings
from rest_framework.test import APIClient

from apps.clinica.factories import (
    AdminFactory,
    FonoFactory,
    PacienteFactory,
    ResponsavelFactory,
    TOFactory,
    UsuarioFactory,
)
from apps.clinica.models import AvaliacaoFono, Registro, TipoUsuario

pytestmark = pytest.mark.django_db
OPCOES = {"DEBUG": True, "WEB_CONSULTA_HABILITADA": True, "ADMIN_CLINICO_DADOS_FICTICIOS": True}


@override_settings(**OPCOES)
def test_admin_visualiza_categorias_privadas_e_autoria_real():
    paciente, admin = PacienteFactory(), AdminFactory()
    for profissional in [FonoFactory(), TOFactory()]:
        Registro.objects.create(
            paciente=paciente,
            autor=profissional,
            categoria=profissional.tipo,
            detalhe="Detalhe privado",
            compartilhado=False,
        )
    client = APIClient()
    client.force_authenticate(admin)
    r = client.get("/api/v1/registros/", {"paciente": str(paciente.pk)})
    assert r.status_code == 200 and r.data["count"] == 2
    assert all(item["detalhe"] == "Detalhe privado" for item in r.data["results"])
    dados = {"paciente": str(paciente.pk), "detalhe": "Fictício", "categoria_simulada": "to"}
    criado = client.post("/api/v1/registros/", dados, format="json")
    assert criado.status_code == 201, criado.data
    assert str(criado.data["autor"]) == str(admin.pk)
    assert criado.data["categoria"] == "to"
    assert (
        client.post(
            "/api/v1/registros/", {"paciente": str(paciente.pk), "detalhe": "teste"}, format="json"
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/registros/", {**dados, "autor": str(admin.pk)}, format="json"
        ).status_code
        == 400
    )


@override_settings(**OPCOES)
def test_admin_cria_revisa_planeja_e_registra_sem_vinculo():
    paciente, admin = PacienteFactory(), AdminFactory()
    client = APIClient()
    client.force_authenticate(admin)
    a = client.post(
        "/api/v1/avaliacoes-fono/",
        {
            "paciente": str(paciente.pk),
            "data": "2026-01-01",
            "protocolo": "Teste fictício",
            "dificuldades_informadas": ["Dificuldade teste"],
        },
        format="json",
    )
    assert a.status_code == 201, a.data
    assert str(a.data["autor"]) == str(admin.pk)
    d = a.data["dificuldades"][0]["id"]
    revisao = client.post(
        f"/api/v1/dificuldades-fono/{d}/revisoes/",
        {"decisao": "aprovado", "texto": "Objetivo teste"},
        format="json",
    )
    assert revisao.status_code == 201 and str(revisao.data["autor"]) == str(admin.pk)
    plano = client.post(
        "/api/v1/planos-fono/",
        {
            "paciente": str(paciente.pk),
            "inicio": "2026-01-01",
            "fim": "2026-06-01",
            "itens_informados": [{"revisao": revisao.data["id"], "meta": "Meta teste"}],
        },
        format="json",
    )
    assert plano.status_code == 201 and str(plano.data["autor"]) == str(admin.pk)
    objetivo = plano.data["itens"][0]["id"]
    sessao = client.post(
        "/api/v1/sessoes-fono/",
        {
            "paciente": str(paciente.pk),
            "data": "2026-02-01",
            "atividade": "Atividade teste",
            "objetivo": objetivo,
            "tentativas": ["I", "E"],
        },
        format="json",
    )
    assert sessao.status_code == 201 and str(sessao.data["autor"]) == str(admin.pk)
    for nome in ["avaliacoes-fono", "planos-fono", "sessoes-fono"]:
        assert client.get(f"/api/v1/{nome}/", {"paciente": str(paciente.pk)}).data["count"] == 1
    assert (
        client.get(
            "/api/v1/sessoes-fono/evolucao/",
            {
                "paciente": str(paciente.pk),
                "objetivo": objetivo,
                "inicio": "2026-01-01",
                "fim": "2026-03-01",
            },
        ).data["pontos"][0]["total"]
        == 2
    )
    web = Client()
    web.force_login(admin)
    pagina = web.get("/")
    assert pagina.status_code == 200
    assert b'id="avaliacoes-fono"' in pagina.content
    assert "ações ficam identificadas como administrativas" in pagina.content.decode()


@pytest.mark.parametrize(
    "alteracao",
    [
        {"DEBUG": False},
        {"ADMIN_CLINICO_DADOS_FICTICIOS": False},
        {"WEB_CONSULTA_HABILITADA": False},
    ],
)
def test_admin_sem_excecao_nao_tem_acesso_clinico(alteracao, settings):
    for nome, valor in {**OPCOES, **alteracao}.items():
        setattr(settings, nome, valor)
    paciente, admin = PacienteFactory(), AdminFactory()
    c = APIClient()
    c.force_authenticate(admin)
    assert c.get("/api/v1/registros/", {"paciente": str(paciente.pk)}).status_code == 403
    assert c.get("/api/v1/avaliacoes-fono/", {"paciente": str(paciente.pk)}).status_code in (
        403,
        404,
    )


@override_settings(**OPCOES)
def test_ti_nao_ganha_acesso():
    paciente, ti = PacienteFactory(), UsuarioFactory(tipo=TipoUsuario.TI)
    c = APIClient()
    c.force_authenticate(ti)
    assert c.get("/api/v1/registros/", {"paciente": str(paciente.pk)}).status_code == 403
    assert c.get("/api/v1/avaliacoes-fono/", {"paciente": str(paciente.pk)}).status_code == 403


@override_settings(**OPCOES)
def test_correcoes_aditivas_e_evolucao_sem_duplicacao():
    paciente, admin = PacienteFactory(), AdminFactory()
    client = APIClient()
    client.force_authenticate(admin)
    a_dados = {
        "paciente": str(paciente.pk),
        "data": "2026-01-01",
        "protocolo": "Ficha",
        "dificuldades_informadas": ["Dificuldade inicial"],
    }
    a = client.post("/api/v1/avaliacoes-fono/", a_dados, format="json").data
    d = a["dificuldades"][0]["id"]
    revisao = client.post(
        f"/api/v1/dificuldades-fono/{d}/revisoes/",
        {"decisao": "aprovado", "texto": "Objetivo inicial"},
        format="json",
    ).data
    p_dados = {
        "paciente": str(paciente.pk),
        "inicio": "2026-01-01",
        "fim": "2026-06-01",
        "itens_informados": [{"revisao": revisao["id"], "meta": "Meta inicial"}],
    }
    plano = client.post("/api/v1/planos-fono/", p_dados, format="json").data
    item = plano["itens"][0]["id"]
    sessao_dados = {
        "paciente": str(paciente.pk),
        "data": "2026-02-01",
        "atividade": "Sessão inicial",
        "objetivo": item,
        "tentativas": ["I", "E"],
    }
    sessao = client.post("/api/v1/sessoes-fono/", sessao_dados, format="json").data
    alterada = client.post(
        "/api/v1/sessoes-fono/",
        {
            **sessao_dados,
            "corrige": sessao["id"],
            "atividade": "Sessão corrigida",
            "tentativas": ["I"],
        },
        format="json",
    )
    assert alterada.status_code == 201
    assert str(alterada.data["autor"]) == str(admin.pk)
    assert (
        client.post(
            "/api/v1/sessoes-fono/", {**sessao_dados, "corrige": sessao["id"]}, format="json"
        ).status_code
        == 400
    )
    historico = client.get("/api/v1/sessoes-fono/", {"paciente": str(paciente.pk)}).data["results"]
    assert next(x for x in historico if x["id"] == sessao["id"])["corrigida"] is True
    grafico = client.get(
        "/api/v1/sessoes-fono/evolucao/",
        {
            "paciente": str(paciente.pk),
            "objetivo": item,
            "inicio": "2026-01-01",
            "fim": "2026-03-01",
        },
    )
    assert grafico.data["pontos"][0]["total"] == 1
    assert grafico.data["pontos"][0]["percentual_independentes"] == 100
    plano2 = client.post("/api/v1/planos-fono/", {**p_dados, "corrige": plano["id"]}, format="json")
    assert plano2.status_code == 201
    assert (
        client.post(
            "/api/v1/planos-fono/", {**p_dados, "corrige": plano["id"]}, format="json"
        ).status_code
        == 400
    )
    a2 = client.post(
        "/api/v1/avaliacoes-fono/",
        {**a_dados, "corrige": a["id"], "dificuldades_informadas": ["Dificuldade corrigida"]},
        format="json",
    )
    assert a2.status_code == 201
    assert (
        client.post(
            "/api/v1/avaliacoes-fono/", {**a_dados, "corrige": a["id"]}, format="json"
        ).status_code
        == 400
    )
    assert (
        client.post(
            f"/api/v1/dificuldades-fono/{d}/revisoes/",
            {"decisao": "aprovado", "texto": "não usar"},
            format="json",
        ).status_code
        == 400
    )
    assert client.post("/api/v1/planos-fono/", p_dados, format="json").status_code == 400
    assert client.get(f"/api/v1/avaliacoes-fono/{a['id']}/").data["corrigida"] is True
    assert client.get(f"/api/v1/planos-fono/{plano['id']}/").data["corrigido"] is True


@override_settings(**OPCOES)
def test_correcao_nao_cruza_pacientes():
    a, b, admin = PacienteFactory(), PacienteFactory(), AdminFactory()
    client = APIClient()
    client.force_authenticate(admin)
    dados = {
        "paciente": str(a.pk),
        "data": "2026-01-01",
        "protocolo": "Ficha",
        "dificuldades_informadas": [],
    }
    original = client.post("/api/v1/avaliacoes-fono/", dados, format="json").data
    assert (
        client.post(
            "/api/v1/avaliacoes-fono/",
            {**dados, "paciente": str(b.pk), "corrige": original["id"]},
            format="json",
        ).status_code
        == 400
    )


@pytest.mark.skipif(connection.vendor != "postgresql", reason="Trigger apenas em PostgreSQL")
@override_settings(**OPCOES)
def test_postgres_impede_correcao_de_outro_paciente():
    primeiro, outro, admin = PacienteFactory(), PacienteFactory(), AdminFactory()
    original = AvaliacaoFono.objects.create(
        paciente=primeiro, autor=admin, data="2026-01-01", protocolo="Teste"
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        AvaliacaoFono.objects.create(
            paciente=outro, autor=admin, data="2026-01-01", protocolo="Teste", corrige=original
        )


@override_settings(**OPCOES)
def test_admin_ve_cadastro_e_responsaveis_ficticios_por_paciente():
    paciente, admin = PacienteFactory(), AdminFactory()
    responsavel = ResponsavelFactory(paciente=paciente)
    outro = ResponsavelFactory()
    c = APIClient()
    c.force_authenticate(admin)
    resposta = c.get(f"/api/v1/pacientes/{paciente.pk}/")
    assert resposta.status_code == 200 and "cpf" in resposta.data
    lista = c.get("/api/v1/responsaveis/", {"paciente": str(paciente.pk)})
    assert lista.status_code == 200 and lista.data["count"] == 1
    assert lista.data["results"][0]["nome"] == responsavel.nome_cifrado
    assert lista.data["results"][0]["cpf"] == responsavel.cpf_cifrado
    assert str(outro.pk) != lista.data["results"][0]["id"]
    assert c.get("/api/v1/responsaveis/", {"paciente": "invalido"}).status_code == 400


@override_settings(**OPCOES)
def test_correcao_de_sessao_em_outro_dia_nao_reconta_original():
    paciente, admin = PacienteFactory(), AdminFactory()
    client = APIClient()
    client.force_authenticate(admin)
    a = client.post(
        "/api/v1/avaliacoes-fono/",
        {
            "paciente": str(paciente.pk),
            "data": "2026-01-01",
            "protocolo": "Ficha",
            "dificuldades_informadas": ["Dificuldade"],
        },
        format="json",
    ).data
    d = a["dificuldades"][0]["id"]
    rev = client.post(
        f"/api/v1/dificuldades-fono/{d}/revisoes/",
        {"decisao": "aprovado", "texto": "Objetivo"},
        format="json",
    ).data
    plano = client.post(
        "/api/v1/planos-fono/",
        {
            "paciente": str(paciente.pk),
            "inicio": "2026-01-01",
            "fim": "2026-12-31",
            "itens_informados": [{"revisao": rev["id"], "meta": "Meta"}],
        },
        format="json",
    ).data
    item = plano["itens"][0]["id"]
    dados = {
        "paciente": str(paciente.pk),
        "data": "2026-01-10",
        "atividade": "Teste",
        "objetivo": item,
        "tentativas": ["I"],
    }
    original = client.post("/api/v1/sessoes-fono/", dados, format="json").data
    assert (
        client.post(
            "/api/v1/sessoes-fono/",
            {**dados, "data": "2026-02-10", "corrige": original["id"]},
            format="json",
        ).status_code
        == 201
    )
    r = client.get(
        "/api/v1/sessoes-fono/evolucao/",
        {
            "paciente": str(paciente.pk),
            "objetivo": item,
            "inicio": "2026-01-01",
            "fim": "2026-01-31",
        },
    )
    assert r.status_code == 200 and r.data["pontos"] == []
    assert (
        client.patch(
            f"/api/v1/sessoes-fono/{original['id']}/", {"atividade": "mudança"}, format="json"
        ).status_code
        == 405
    )
