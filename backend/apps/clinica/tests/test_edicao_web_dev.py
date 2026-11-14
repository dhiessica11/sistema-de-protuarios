"""Edição administrativa exige justificativa para identidade e detecta versão antiga."""

import pytest
from django.test import Client, override_settings
from rest_framework.test import APIClient

from apps.clinica.factories import AdminFactory, FonoFactory, PacienteFactory, ResponsavelFactory
from apps.clinica.models import AlteracaoCadastral

pytestmark = pytest.mark.django_db
OPCOES = {"DEBUG": True, "WEB_CONSULTA_HABILITADA": True, "ADMIN_CLINICO_DADOS_FICTICIOS": True}


@override_settings(**OPCOES)
def test_justificativa_e_conflito_em_paciente():
    admin, paciente = AdminFactory(), PacienteFactory()
    c = APIClient()
    c.force_authenticate(admin)
    url = f"/api/v1/pacientes/{paciente.pk}/"
    versao = c.get(url).data["atualizado_em"]
    assert (
        c.patch(
            url, {"nome_civil": "Nome fictício corrigido", "versao_esperada": versao}, format="json"
        ).status_code
        == 400
    )
    resposta = c.patch(
        url,
        {
            "nome_civil": "Nome fictício corrigido",
            "versao_esperada": versao,
            "justificativa_alteracao": "Correção do cadastro fictício",
        },
        format="json",
    )
    assert resposta.status_code == 200
    assert AlteracaoCadastral.objects.get().autor_id == admin.pk
    conflito = c.patch(
        url, {"telefone_cifrado": "123456", "versao_esperada": versao}, format="json"
    )
    assert conflito.status_code == 409
    paciente.refresh_from_db()
    assert paciente.telefone_cifrado != "123456"


@override_settings(**OPCOES)
def test_conflito_em_responsavel_e_contato_sem_justificativa():
    admin, responsavel = AdminFactory(), ResponsavelFactory()
    c = APIClient()
    c.force_authenticate(admin)
    url = f"/api/v1/responsaveis/{responsavel.pk}/"
    versao = c.get(url).data["atualizado_em"]
    assert (
        c.patch(
            url, {"telefone_cifrado": "123456", "versao_esperada": versao}, format="json"
        ).status_code
        == 200
    )
    assert not AlteracaoCadastral.objects.exists()
    assert (
        c.patch(
            url,
            {
                "nome": "Outro nome",
                "versao_esperada": versao,
                "justificativa_alteracao": "Correção do cadastro fictício",
            },
            format="json",
        ).status_code
        == 409
    )
    responsavel.refresh_from_db()
    assert responsavel.nome_cifrado != "Outro nome"


@override_settings(**OPCOES)
def test_somente_admin_ve_editores():
    c = Client()
    c.force_login(AdminFactory())
    conteudo = c.get("/").content
    assert b'id="form-editar-paciente"' in conteudo
    assert b'id="form-editar-responsavel"' in conteudo
    c.force_login(FonoFactory())
    conteudo = c.get("/").content
    assert b'id="form-editar-paciente"' not in conteudo
    assert b'id="form-editar-responsavel"' not in conteudo
