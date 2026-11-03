"""TI nao recebe permissoes clinicas ou promocao via Django Admin."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.clinica.factories import AdminFactory, ClinicaFactory, PacienteFactory, ResponsavelFactory
from apps.clinica.models import TipoUsuario

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def staticfiles_sem_manifesto(settings):
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }


@pytest.fixture
def tecnico():
    return get_user_model().objects.create_superuser(
        username="tecnico", password="senha-sintetica-123"
    )


@pytest.mark.parametrize(
    "endpoint",
    [
        "pacientes",
        "responsaveis",
        "consentimentos",
        "paciente-equipe",
        "registros",
        "usuarios",
        "clinicas",
    ],
)
def test_tecnico_superusuario_nao_acessa_api_da_clinica(tecnico, endpoint):
    PacienteFactory()
    client = APIClient()
    client.force_authenticate(tecnico)
    assert tecnico.tipo == TipoUsuario.TI and not tecnico.eh_admin
    assert client.get(f"/api/v1/{endpoint}/").status_code == 403
    assert client.post(f"/api/v1/{endpoint}/", {}, format="json").status_code in (403, 405)


def test_tecnico_nao_altera_perfil_proprio_ou_de_outro_usuario(tecnico, client):
    admin = AdminFactory()
    client.force_login(tecnico)
    assert client.get("/admin/").status_code == 200
    assert client.get("/admin/clinica/usuario/").status_code == 403
    assert client.get("/admin/clinica/usuario/add/").status_code == 403
    assert (
        client.post("/admin/clinica/usuario/add/", {"tipo": TipoUsuario.ADMIN}).status_code == 403
    )
    assert client.get(f"/admin/clinica/usuario/{tecnico.pk}/password/").status_code == 403
    for user in (tecnico, admin):
        url = f"/admin/clinica/usuario/{user.pk}/change/"
        assert client.get(url).status_code == 403
        assert client.post(url, {"tipo": TipoUsuario.ADMIN}).status_code == 403
    tecnico.refresh_from_db()
    assert tecnico.tipo == TipoUsuario.TI


def test_tecnico_nao_acessa_detalhe_nem_edita_paciente(tecnico):
    paciente = PacienteFactory()
    client = APIClient()
    client.force_authenticate(tecnico)
    url = f"/api/v1/pacientes/{paciente.pk}/"
    assert client.get(url).status_code == 403
    assert client.patch(url, {"status": "pausado"}, format="json").status_code == 403
    paciente.refresh_from_db()
    assert paciente.status == "ativo"


def test_tecnico_nao_modifica_clinica_no_admin(tecnico, client):
    clinica = ClinicaFactory()
    nome = clinica.nome
    client.force_login(tecnico)
    url = f"/admin/clinica/clinica/{clinica.pk}/change/"
    assert client.post(url, {"nome": "Nome adulterado"}).status_code == 403
    assert client.get("/admin/clinica/clinica/add/").status_code == 403
    clinica.refresh_from_db()
    assert clinica.nome == nome


def test_login_admin_permanece_acessivel_anonimamente(client):
    assert client.get("/admin/login/").status_code == 200


def test_profissional_superusuario_nao_promove_proprio_perfil(client):
    profissional = get_user_model().objects.create_superuser(
        username="fono-super", password="senha-sintetica-123", tipo=TipoUsuario.FONO
    )
    client.force_login(profissional)
    url = f"/admin/clinica/usuario/{profissional.pk}/change/"
    assert client.get(url).status_code == 403
    assert client.post(url, {"tipo": TipoUsuario.ADMIN}).status_code == 403
    profissional.refresh_from_db()
    assert profissional.tipo == TipoUsuario.FONO


def test_admin_clinica_mantem_acesso_api_e_admin_django(client):
    user = get_user_model().objects.create_superuser(
        username="admin-clinica", password="senha-sintetica-123", tipo=TipoUsuario.ADMIN
    )
    paciente = PacienteFactory()
    ResponsavelFactory(paciente=paciente)
    api = APIClient()
    api.force_authenticate(user)
    assert user.eh_admin
    assert api.get(f"/api/v1/pacientes/{paciente.pk}/").status_code == 200
    client.force_login(user)
    assert client.get("/admin/clinica/usuario/").status_code == 200
