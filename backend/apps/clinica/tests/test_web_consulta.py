"""A interface usa sessão e mantém as permissões da API de registros."""

import pytest
from django.test import Client, override_settings
from rest_framework.test import APIClient

from apps.clinica.factories import (
    FonoFactory,
    PacienteEquipeFactory,
    PacienteFactory,
    TOFactory,
    UsuarioFactory,
)
from apps.clinica.models import Registro, TipoUsuario

pytestmark = pytest.mark.django_db


@override_settings(WEB_CONSULTA_HABILITADA=True)
def test_login_logout_e_csrf():
    user = FonoFactory()
    client = Client(enforce_csrf_checks=True)
    assert client.get("/").status_code == 302
    entrada = client.get("/entrar/")
    assert entrada.status_code == 200
    assert b"/static/clinica/web.css" in entrada.content
    assert (
        client.post(
            "/entrar/", {"username": user.username, "password": "senha-de-teste-12chars"}
        ).status_code
        == 403
    )
    token = entrada.cookies["csrftoken"].value
    resposta = client.post(
        "/entrar/",
        {
            "username": user.username,
            "password": "senha-de-teste-12chars",
            "csrfmiddlewaretoken": token,
        },
    )
    assert resposta.status_code == 302
    tela = client.get("/")
    assert tela.status_code == 200
    assert "no-store" in tela["Cache-Control"]
    assert client.get("/sair/").status_code == 405
    token = client.cookies["csrftoken"].value
    assert client.post("/sair/", {"csrfmiddlewaretoken": token}).status_code == 302
    assert client.get("/").status_code == 302


def test_interface_desligada_por_padrao():
    client = Client()
    assert client.get("/entrar/").status_code == 404


@override_settings(WEB_CONSULTA_HABILITADA=True)
def test_ti_nao_acessa_tela():
    ti = UsuarioFactory(tipo=TipoUsuario.TI)
    client = Client()
    client.force_login(ti)
    assert client.get("/").status_code == 403


def test_filtro_paciente_mantem_privacidade_e_escopo():
    paciente, outro = PacienteFactory(), PacienteFactory()
    fono, to = FonoFactory(), TOFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=to)
    Registro.objects.create(
        paciente=paciente,
        autor=fono,
        categoria=fono.tipo,
        resumo="Compartilhado",
        detalhe="privado",
        compartilhado=True,
    )
    Registro.objects.create(
        paciente=outro,
        autor=fono,
        categoria=fono.tipo,
        resumo="Fora do escopo",
        detalhe="privado",
        compartilhado=True,
    )
    client = APIClient()
    client.force_authenticate(to)
    resposta = client.get("/api/v1/registros/", {"paciente": str(paciente.pk)})
    assert resposta.status_code == 200
    assert resposta.data["count"] == 1
    assert resposta.data["results"][0]["resumo"] == "Compartilhado"
    assert "detalhe" not in resposta.data["results"][0]
    assert client.get("/api/v1/registros/", {"paciente": str(outro.pk)}).data["count"] == 0
    assert client.get("/api/v1/registros/", {"paciente": "inválido"}).status_code == 400
