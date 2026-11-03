"""
Testes de AUTORIZACAO da API.

Cada endpoint testado em 3 perfis: anonimo, profissional nao-vinculado,
profissional vinculado, admin. Mais testes de DELETE bloqueado e escopo.
"""

import pytest
from rest_framework.test import APIClient

from apps.clinica.factories import (
    AdminFactory,
    ConsentimentoFactory,
    FonoFactory,
    PacienteEquipeFactory,
    PacienteFactory,
    ResponsavelFactory,
)


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def fono_sem_pacientes(db):
    return FonoFactory(username="fono_sem")


@pytest.fixture
def fono_com_paciente(db):
    fono = FonoFactory(username="fono_com")
    paciente = PacienteFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=fono, ativo=True)
    return fono, paciente


@pytest.fixture
def admin_user(db):
    return AdminFactory(username="admin_test")


# -----------------------------------------------------------------------------
# ANONIMO - nao acessa nada
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestAnonimoBloqueado:
    def test_lista_pacientes_bloqueada(self, client):
        resp = client.get("/api/v1/pacientes/")
        assert resp.status_code in (401, 403)

    def test_lista_consentimentos_bloqueada(self, client):
        resp = client.get("/api/v1/consentimentos/")
        assert resp.status_code in (401, 403)

    def test_lista_vinculos_bloqueada(self, client):
        resp = client.get("/api/v1/paciente-equipe/")
        assert resp.status_code in (401, 403)


# -----------------------------------------------------------------------------
# PROFISSIONAL SO VE SEUS PACIENTES
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestProfissionalEscopo:
    def test_fono_sem_vinculo_nao_ve_paciente(self, client, fono_sem_pacientes):
        PacienteFactory()  # paciente de outra equipe
        client.force_authenticate(user=fono_sem_pacientes)
        resp = client.get("/api/v1/pacientes/")
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_fono_com_vinculo_ve_seu_paciente(self, client, fono_com_paciente):
        fono, paciente = fono_com_paciente
        PacienteFactory()  # outro
        client.force_authenticate(user=fono)
        resp = client.get("/api/v1/pacientes/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["id"] == str(paciente.id)

    def test_fono_nao_pode_criar_paciente(self, client, fono_sem_pacientes):
        """So admin cadastra - permissao avaliada ANTES do serializer."""
        client.force_authenticate(user=fono_sem_pacientes)
        resp = client.post("/api/v1/pacientes/", {}, format="json")
        # Deve ser 403 (permissao), nao 400 (validacao)
        assert resp.status_code == 403


# -----------------------------------------------------------------------------
# ADMIN VE E GERENCIA TUDO
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestAdminAcessoTotal:
    def test_admin_lista_todos_pacientes(self, client, admin_user):
        PacienteFactory()
        PacienteFactory()
        client.force_authenticate(user=admin_user)
        resp = client.get("/api/v1/pacientes/")
        assert resp.status_code == 200
        assert resp.json()["count"] == 2


# -----------------------------------------------------------------------------
# DELETE BLOQUEADO EM TODOS CLINICOS (CFFa 777 guarda permanente)
# Retorna 405 Method Not Allowed via http_method_names.
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestDeleteBloqueado:
    def test_admin_nao_pode_deletar_paciente(self, client, admin_user):
        p = PacienteFactory()
        client.force_authenticate(user=admin_user)
        resp = client.delete(f"/api/v1/pacientes/{p.id}/")
        assert resp.status_code == 405

    def test_admin_nao_pode_deletar_responsavel(self, client, admin_user):
        r = ResponsavelFactory()
        client.force_authenticate(user=admin_user)
        resp = client.delete(f"/api/v1/responsaveis/{r.id}/")
        assert resp.status_code == 405

    def test_admin_nao_pode_deletar_vinculo_equipe(self, client, admin_user):
        v = PacienteEquipeFactory()
        client.force_authenticate(user=admin_user)
        resp = client.delete(f"/api/v1/paciente-equipe/{v.id}/")
        assert resp.status_code == 405

    def test_consentimento_sem_update_sem_delete(self, client, admin_user):
        c = ConsentimentoFactory()
        client.force_authenticate(user=admin_user)
        assert client.put(f"/api/v1/consentimentos/{c.id}/", {}).status_code == 405
        assert client.patch(f"/api/v1/consentimentos/{c.id}/", {}).status_code == 405
        assert client.delete(f"/api/v1/consentimentos/{c.id}/").status_code == 405


# -----------------------------------------------------------------------------
# VINCULO EQUIPE: SO ADMIN CRIA/EDITA
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestVinculoEquipeSoAdmin:
    def test_fono_nao_pode_criar_vinculo(self, client, fono_com_paciente):
        fono, _ = fono_com_paciente
        client.force_authenticate(user=fono)
        resp = client.post("/api/v1/paciente-equipe/", {}, format="json")
        assert resp.status_code == 403

    def test_admin_pode_criar_vinculo(self, client, admin_user):
        paciente = PacienteFactory()
        fono = FonoFactory()
        client.force_authenticate(user=admin_user)
        resp = client.post(
            "/api/v1/paciente-equipe/",
            {
                "paciente": str(paciente.id),
                "profissional": str(fono.id),
            },
            format="json",
        )
        assert resp.status_code == 201

    def test_fono_ve_apenas_seus_vinculos(self, client, fono_com_paciente):
        fono, _ = fono_com_paciente
        PacienteEquipeFactory()  # vinculo de outro
        client.force_authenticate(user=fono)
        resp = client.get("/api/v1/paciente-equipe/")
        assert resp.status_code == 200
        for item in resp.json()["results"]:
            assert item["profissional"] == str(fono.id)


# -----------------------------------------------------------------------------
# CONSENTIMENTO - ESCOPO E INTEGRIDADE
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestConsentimentoEscopo:
    def test_fono_nao_cria_consentimento_fora_do_escopo(self, client, fono_com_paciente):
        """
        Fono tem paciente A. Tenta criar consentimento para paciente B
        (fora da equipe dele). Deve ser bloqueado no serializer.
        """
        fono, _paciente_proprio = fono_com_paciente
        paciente_outro = PacienteFactory()
        responsavel = ResponsavelFactory(paciente=paciente_outro)
        client.force_authenticate(user=fono)
        resp = client.post(
            "/api/v1/consentimentos/",
            {
                "paciente": str(paciente_outro.id),
                "responsavel": str(responsavel.id),
                "tipo": "lgpd_geral",
                "texto_apresentado": "teste",
                "aceito": True,
            },
            format="json",
        )
        assert resp.status_code == 400
        assert "escopo" in str(resp.json()).lower()

    def test_responsavel_deve_pertencer_ao_paciente(self, client, admin_user):
        """
        Admin tenta criar consentimento com responsavel de OUTRO paciente.
        Serializer bloqueia.
        """
        paciente_a = PacienteFactory()
        paciente_b = PacienteFactory()
        responsavel_b = ResponsavelFactory(paciente=paciente_b)
        client.force_authenticate(user=admin_user)
        resp = client.post(
            "/api/v1/consentimentos/",
            {
                "paciente": str(paciente_a.id),
                "responsavel": str(responsavel_b.id),
                "tipo": "lgpd_geral",
                "texto_apresentado": "teste",
                "aceito": True,
            },
            format="json",
        )
        assert resp.status_code == 400
