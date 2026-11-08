"""Cadastro web de dados fictícios usa a API e exige sessão administrativa e CSRF."""

import json

import pytest
from django.test import Client, override_settings
from rest_framework.test import APIClient

from apps.clinica.factories import AdminFactory, ClinicaFactory, FonoFactory
from apps.clinica.models import Paciente, Responsavel

pytestmark = pytest.mark.django_db
OPCOES = {"DEBUG": True, "WEB_CONSULTA_HABILITADA": True, "ADMIN_CLINICO_DADOS_FICTICIOS": True}


@override_settings(**OPCOES)
def test_formulario_admin_e_cadastro_com_csrf():
    admin, clinica = AdminFactory(), ClinicaFactory()
    c = Client(enforce_csrf_checks=True)
    c.force_login(admin)
    pagina = c.get("/")
    assert pagina.status_code == 200
    assert b'id="form-novo-paciente"' in pagina.content
    assert b'id="form-novo-responsavel"' in pagina.content
    payload = {
        "clinica": str(clinica.pk),
        "nome_civil": "Criança fictícia",
        "nome_social": "",
        "data_nascimento": "2020-01-02",
        "sexo": "O",
        "cpf": "",
    }
    assert (
        c.post(
            "/api/v1/pacientes/", json.dumps(payload), content_type="application/json"
        ).status_code
        == 403
    )
    token = c.cookies["csrftoken"].value
    resposta = c.post(
        "/api/v1/pacientes/",
        json.dumps(payload),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert resposta.status_code == 201, resposta.content
    paciente_id = resposta.json()["id"]
    assert Paciente.objects.get(pk=paciente_id).criado_por_id == admin.pk
    responsavel = {
        "paciente": paciente_id,
        "nome": "Responsável fictício",
        "cpf": "52998224725",
        "vinculo": "outro",
        "telefone_cifrado": "",
        "email": "",
        "eh_responsavel_legal_principal": False,
    }
    invalido = c.post(
        "/api/v1/responsaveis/",
        json.dumps({**responsavel, "cpf": "11111111111"}),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert invalido.status_code == 400
    assert not Responsavel.objects.filter(paciente_id=paciente_id).exists()
    valido = c.post(
        "/api/v1/responsaveis/",
        json.dumps(responsavel),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert valido.status_code == 201, valido.content
    assert Responsavel.objects.get(paciente_id=paciente_id).criado_por_id == admin.pk


@override_settings(**OPCOES)
def test_profissional_nao_cadastra_e_nao_ve_formulario():
    fono, clinica = FonoFactory(), ClinicaFactory()
    web = Client()
    web.force_login(fono)
    assert b'id="form-novo-paciente"' not in web.get("/").content
    api = APIClient()
    api.force_authenticate(fono)
    payload = {
        "clinica": str(clinica.pk),
        "nome_civil": "Fictício",
        "data_nascimento": "2020-01-01",
        "sexo": "O",
    }
    assert api.post("/api/v1/pacientes/", payload, format="json").status_code == 403


@override_settings(DEBUG=False, WEB_CONSULTA_HABILITADA=True, ADMIN_CLINICO_DADOS_FICTICIOS=True)
def test_formulario_nao_aparece_quando_debug_desligado():
    admin = AdminFactory()
    c = Client()
    c.force_login(admin)
    pagina = c.get("/")
    assert pagina.status_code == 200
    assert b'id="form-novo-paciente"' not in pagina.content


@pytest.mark.parametrize("digito", "0123456789")
def test_cpf_com_digitos_repetidos_e_invalido(digito):
    from django.core.exceptions import ValidationError

    from apps.core.validators import validar_cpf

    with pytest.raises(ValidationError):
        validar_cpf(digito * 11)
