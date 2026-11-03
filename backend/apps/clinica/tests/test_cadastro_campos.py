"""Autorizacao por campo, identidade justificada e persistencia atomica."""

from types import SimpleNamespace

import pytest
from django.contrib import admin
from django.db import connection
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.clinica.factories import (
    AdminFactory,
    ClinicaFactory,
    PacienteEquipeFactory,
    PacienteFactory,
    ResponsavelFactory,
    UsuarioFactory,
    fake,
)
from apps.clinica.models import AlteracaoCadastral, Paciente, Responsavel, TipoUsuario
from apps.clinica.serializers import PacienteSerializer
from apps.core.validators import hash_cpf, normalizar_cpf

pytestmark = pytest.mark.django_db


@pytest.fixture(params=[TipoUsuario.FONO, TipoUsuario.TO, TipoUsuario.PSICO])
def clinico(request):
    user = UsuarioFactory(tipo=request.param)
    paciente = PacienteFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=user)
    client = APIClient()
    client.force_authenticate(user)
    return client, user, paciente


@pytest.fixture
def admin_client():
    client = APIClient()
    user = AdminFactory()
    client.force_authenticate(user)
    return client, user


@pytest.mark.parametrize("method", ["patch", "put"])
@pytest.mark.parametrize("campo", ["nome_civil", "cpf", "telefone_cifrado", "data_nascimento"])
def test_clinico_nao_altera_cadastro_restrito_nem_parte_permitida(clinico, method, campo):
    client, _, paciente = clinico
    original = paciente.nome_civil
    response = getattr(client, method)(
        f"/api/v1/pacientes/{paciente.pk}/",
        {campo: "valor invalido de proposito", "status": "pausado"},
        format="json",
    )
    assert response.status_code == 403  # Permissao antes de validar o valor.
    assert campo in response.data
    paciente.refresh_from_db()
    assert paciente.nome_civil == original
    assert paciente.status == "ativo"
    assert not AlteracaoCadastral.objects.exists()


def test_clinico_vinculado_altera_campos_clinicos_e_nome_social(clinico):
    client, user, paciente = clinico
    response = client.patch(
        f"/api/v1/pacientes/{paciente.pk}/",
        {
            "nome_social": "Nome social de teste",
            "status": "encerrado",
            "data_encerramento": "2026-01-01",
        },
        format="json",
    )
    assert response.status_code == 200
    paciente.refresh_from_db()
    assert paciente.nome_social == "Nome social de teste"
    assert paciente.status == "encerrado"
    assert str(paciente.data_encerramento) == "2026-01-01"
    assert paciente.atualizado_por_id == user.pk
    assert not AlteracaoCadastral.objects.exists()


@pytest.mark.parametrize("ativo", [False, None])
def test_clinico_sem_vinculo_ativo_nao_atualiza(clinico, ativo):
    client, user, paciente = clinico
    if ativo is None:
        PacienteEquipeFactory(paciente=PacienteFactory(), profissional=user)
        paciente = PacienteFactory()
    else:
        paciente.equipe.update(ativo=False)
    response = client.patch(
        f"/api/v1/pacientes/{paciente.pk}/", {"status": "pausado"}, format="json"
    )
    assert response.status_code == 404
    paciente.refresh_from_db()
    assert paciente.status == "ativo"


@pytest.mark.parametrize(
    "campo",
    [
        "guarda_compartilhada",
        "eh_responsavel_legal_principal",
        "ativo",
        "telefone_cifrado",
        "nome",
        "cpf",
    ],
)
@pytest.mark.parametrize("method", ["put", "patch"])
def test_clinico_nao_edita_responsavel(clinico, campo, method):
    client, _, paciente = clinico
    responsavel = ResponsavelFactory(paciente=paciente)
    response = getattr(client, method)(
        f"/api/v1/responsaveis/{responsavel.pk}/", {campo: False}, format="json"
    )
    assert response.status_code == 403
    responsavel.refresh_from_db()
    assert responsavel.ativo
    assert responsavel.eh_responsavel_legal_principal
    assert not responsavel.guarda_compartilhada


def test_clinico_continua_lendo_cadastros_compartilhados(clinico):
    client, _, paciente = clinico
    responsavel = ResponsavelFactory(paciente=paciente)
    assert client.get(f"/api/v1/pacientes/{paciente.pk}/").status_code == 200
    assert client.get(f"/api/v1/responsaveis/{responsavel.pk}/").status_code == 200


@pytest.mark.parametrize(
    "campo,valor", [("status", "encerrado"), ("data_encerramento", "2026-01-01")]
)
def test_admin_nao_edita_campos_clinicos(admin_client, campo, valor):
    client, _ = admin_client
    paciente = PacienteFactory()
    response = client.patch(f"/api/v1/pacientes/{paciente.pk}/", {campo: valor}, format="json")
    assert response.status_code == 403
    paciente.refresh_from_db()
    assert paciente.status == "ativo"
    assert paciente.data_encerramento is None


@pytest.mark.parametrize("justificativa", [None, "", "   ", "curta"])
def test_identificacao_exige_justificativa_valida(admin_client, justificativa):
    client, _ = admin_client
    paciente = PacienteFactory()
    original = paciente.nome_civil
    payload = {"nome_civil": "Outro nome"}
    if justificativa is not None:
        payload["justificativa_alteracao"] = justificativa
    response = client.patch(f"/api/v1/pacientes/{paciente.pk}/", payload, format="json")
    assert response.status_code == 400
    paciente.refresh_from_db()
    assert paciente.nome_civil == original
    assert not AlteracaoCadastral.objects.exists()


def test_admin_corrige_identificacao_com_evidencia_cifrada(admin_client):
    client, user = admin_client
    paciente = PacienteFactory()
    motivo = "Correcao cadastral conferida no documento apresentado."
    response = client.patch(
        f"/api/v1/pacientes/{paciente.pk}/",
        {"nome_civil": "Nome corrigido", "justificativa_alteracao": motivo},
        format="json",
    )
    assert response.status_code == 200
    paciente.refresh_from_db()
    assert paciente.nome_civil == "Nome corrigido"
    alteracao = AlteracaoCadastral.objects.get()
    assert alteracao.paciente_id == paciente.pk
    assert alteracao.responsavel_id is None
    assert alteracao.autor_id == user.pk
    assert alteracao.campos == ["nome_civil"]
    assert alteracao.justificativa == motivo
    assert "justificativa_alteracao" not in response.data
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT justificativa FROM clinica_alteracaocadastral WHERE id = %s", [alteracao.pk.hex]
        )
        # UUID e adaptado de modo diferente no SQLite e no PostgreSQL.
        row = cursor.fetchone()
    assert row and row[0] != motivo and motivo not in row[0]
    assert AlteracaoCadastral not in admin.site._registry


def test_falha_ao_gravar_justificativa_reverte_alteracao(admin_client, monkeypatch):
    client, _ = admin_client
    paciente = PacienteFactory()
    original = paciente.nome_civil

    def falhar(**kwargs):
        raise RuntimeError("Falha simulada na persistencia da justificativa")

    monkeypatch.setattr(AlteracaoCadastral.objects, "create", falhar)
    with pytest.raises(RuntimeError, match="Falha simulada"):
        client.patch(
            f"/api/v1/pacientes/{paciente.pk}/",
            {"nome_civil": "Nome novo", "justificativa_alteracao": "Correcao documental de teste"},
            format="json",
        )
    paciente.refresh_from_db()
    assert paciente.nome_civil == original
    assert not AlteracaoCadastral.objects.exists()


def test_admin_corrige_cpf_do_paciente_e_remove_hash_ao_esvaziar(admin_client):
    client, _ = admin_client
    paciente = PacienteFactory()
    cpf = fake.cpf()
    url = f"/api/v1/pacientes/{paciente.pk}/"
    for valor in [cpf, ""]:
        response = client.patch(
            url,
            {"cpf": valor, "justificativa_alteracao": "Correcao documental conferida"},
            format="json",
        )
        assert response.status_code == 200
        paciente.refresh_from_db()
        assert (
            paciente.cpf_cifrado == normalizar_cpf(valor) if valor else paciente.cpf_cifrado == ""
        )
        assert paciente.cpf_hash == hash_cpf(cpf) if valor else paciente.cpf_hash is None
    assert AlteracaoCadastral.objects.count() == 2


def test_admin_corrige_nome_e_cpf_do_responsavel(admin_client):
    client, user = admin_client
    responsavel = ResponsavelFactory()
    cpf = fake.cpf()
    response = client.patch(
        f"/api/v1/responsaveis/{responsavel.pk}/",
        {
            "nome": "Nome corrigido",
            "cpf": cpf,
            "justificativa_alteracao": "Correcao documental conferida",
        },
        format="json",
    )
    assert response.status_code == 200
    responsavel.refresh_from_db()
    assert responsavel.nome_cifrado == "Nome corrigido"
    assert responsavel.cpf_cifrado == normalizar_cpf(cpf)
    assert responsavel.cpf_hash == hash_cpf(cpf)
    assert responsavel.atualizado_por_id == user.pk
    alteracao = AlteracaoCadastral.objects.get()
    assert alteracao.responsavel_id == responsavel.pk
    assert alteracao.paciente_id == responsavel.paciente_id
    assert alteracao.campos == ["cpf", "nome"]


def test_identificacao_inalterada_e_contato_nao_exigem_motivo(admin_client):
    client, _ = admin_client
    paciente = PacienteFactory()
    response = client.patch(
        f"/api/v1/pacientes/{paciente.pk}/",
        {"nome_civil": paciente.nome_civil, "telefone_cifrado": "contato de teste"},
        format="json",
    )
    assert response.status_code == 200
    assert not AlteracaoCadastral.objects.exists()


def test_admin_nao_transfere_paciente_de_clinica(admin_client):
    client, _ = admin_client
    paciente = PacienteFactory()
    clinica = paciente.clinica_id
    response = client.patch(
        f"/api/v1/pacientes/{paciente.pk}/", {"clinica": str(ClinicaFactory().pk)}, format="json"
    )
    assert response.status_code == 400
    paciente.refresh_from_db()
    assert paciente.clinica_id == clinica


@pytest.mark.parametrize("campo", ["cpf_hash", "cpf_cifrado", "criado_por", "atualizado_por"])
def test_campos_ocultos_nao_podem_ser_injetados(admin_client, campo):
    client, _ = admin_client
    paciente = PacienteFactory()
    response = client.patch(f"/api/v1/pacientes/{paciente.pk}/", {campo: "forjado"}, format="json")
    assert response.status_code == 400
    paciente.refresh_from_db()
    assert paciente.cpf_hash is None


def test_campo_somente_leitura_e_rejeitado_em_vez_de_ignorado(admin_client):
    client, _ = admin_client
    paciente = PacienteFactory()
    numero = paciente.numero_prontuario
    response = client.patch(
        f"/api/v1/pacientes/{paciente.pk}/", {"numero_prontuario": "forjado"}, format="json"
    )
    assert response.status_code == 403
    paciente.refresh_from_db()
    assert paciente.numero_prontuario == numero


def test_clinico_nao_cria_paciente_mesmo_com_payload_valido(clinico):
    client, _, paciente = clinico
    payload = {
        "clinica": str(paciente.clinica_id),
        "nome_civil": "Paciente sintetico",
        "data_nascimento": "2020-01-01",
        "sexo": "F",
    }
    response = client.post("/api/v1/pacientes/", payload, format="json")
    assert response.status_code == 403


def test_admin_cria_cadastros_com_aliases_cifrados(admin_client):
    client, _ = admin_client
    clinica = ClinicaFactory()
    cpf_paciente, cpf_responsavel = fake.cpf(), fake.cpf()
    response = client.post(
        "/api/v1/pacientes/",
        {
            "clinica": str(clinica.pk),
            "nome_civil": "Paciente sintetico",
            "data_nascimento": "2020-01-01",
            "sexo": "F",
            "cpf": cpf_paciente,
        },
        format="json",
    )
    assert response.status_code == 201
    paciente = Paciente.objects.get(pk=response.data["id"])
    assert paciente.cpf_cifrado == normalizar_cpf(cpf_paciente)
    assert paciente.cpf_hash == hash_cpf(cpf_paciente)
    response = client.post(
        "/api/v1/responsaveis/",
        {
            "paciente": str(paciente.pk),
            "nome": "Responsavel sintetico",
            "cpf": cpf_responsavel,
            "vinculo": "mae",
        },
        format="json",
    )
    assert response.status_code == 201
    responsavel = Responsavel.objects.get(pk=response.data["id"])
    assert responsavel.nome_cifrado == "Responsavel sintetico"
    assert responsavel.cpf_cifrado == normalizar_cpf(cpf_responsavel)
    assert responsavel.cpf_hash == hash_cpf(cpf_responsavel)
    assert not AlteracaoCadastral.objects.exists()


def test_put_administrativo_legitimo_continua_funcionando(admin_client):
    client, _ = admin_client
    paciente = PacienteFactory()
    response = client.put(
        f"/api/v1/pacientes/{paciente.pk}/",
        {
            "clinica": str(paciente.clinica_id),
            "nome_civil": paciente.nome_civil,
            "data_nascimento": str(paciente.data_nascimento),
            "sexo": paciente.sexo,
            "telefone_cifrado": "contato atualizado",
        },
        format="json",
    )
    assert response.status_code == 200
    paciente.refresh_from_db()
    assert paciente.telefone_cifrado == "contato atualizado"
    assert not AlteracaoCadastral.objects.exists()


def test_mesmo_cpf_com_mascara_nao_exige_justificativa(admin_client):
    client, _ = admin_client
    cpf = fake.cpf()
    responsavel = ResponsavelFactory(cpf_cifrado=cpf)
    response = client.patch(
        f"/api/v1/responsaveis/{responsavel.pk}/", {"cpf": normalizar_cpf(cpf)}, format="json"
    )
    assert response.status_code == 200
    assert not AlteracaoCadastral.objects.exists()


def test_clinico_nao_modifica_responsavel_com_payload_vazio(clinico):
    client, _, paciente = clinico
    responsavel = ResponsavelFactory(paciente=paciente)
    antes = responsavel.atualizado_em
    response = client.patch(f"/api/v1/responsaveis/{responsavel.pk}/", {}, format="json")
    assert response.status_code == 403
    responsavel.refresh_from_db()
    assert responsavel.atualizado_em == antes


def test_snapshot_antigo_nao_dispensa_justificativa(admin_client):
    _, user = admin_client
    paciente = PacienteFactory()
    serializer = PacienteSerializer(
        paciente,
        data={"nome_civil": paciente.nome_civil},
        partial=True,
        context={"request": SimpleNamespace(user=user)},
    )
    assert serializer.is_valid(), serializer.errors
    Paciente.objects.filter(pk=paciente.pk).update(nome_civil="Identificacao concorrente")
    with pytest.raises(ValidationError, match="justificativa"):
        serializer.save(atualizado_por=user)
    paciente.refresh_from_db()
    assert paciente.nome_civil == "Identificacao concorrente"
    assert not AlteracaoCadastral.objects.exists()


def test_atualizacao_clinica_nao_desfaz_contato_concorrente(clinico):
    _, user, paciente = clinico
    serializer = PacienteSerializer(
        paciente,
        data={"status": "pausado"},
        partial=True,
        context={"request": SimpleNamespace(user=user)},
    )
    assert serializer.is_valid(), serializer.errors
    Paciente.objects.filter(pk=paciente.pk).update(telefone_cifrado="Contato concorrente")
    serializer.save(atualizado_por=user)
    paciente.refresh_from_db()
    assert paciente.status == "pausado"
    assert paciente.telefone_cifrado == "Contato concorrente"
