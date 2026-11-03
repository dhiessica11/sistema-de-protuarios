"""Um responsavel existente nao pode ser transferido para outro paciente."""

import pytest
from rest_framework.test import APIClient

from apps.clinica.factories import (
    AdminFactory,
    FonoFactory,
    PacienteEquipeFactory,
    PacienteFactory,
    ResponsavelFactory,
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("perfil", ["admin", "fono_com_acesso", "fono_sem_acesso"])
def test_troca_de_paciente_rejeitada_sem_alterar_vinculo(perfil):
    origem = PacienteFactory()
    destino = PacienteFactory(clinica=origem.clinica)
    user = AdminFactory() if perfil == "admin" else FonoFactory()
    if perfil != "admin":
        PacienteEquipeFactory(paciente=origem, profissional=user)
        if perfil == "fono_com_acesso":
            PacienteEquipeFactory(paciente=destino, profissional=user)
    responsavel = ResponsavelFactory(paciente=origem, eh_responsavel_legal_principal=False)
    client = APIClient()
    client.force_authenticate(user)

    response = client.patch(
        f"/api/v1/responsaveis/{responsavel.pk}/",
        {"paciente": str(destino.pk)},
        format="json",
    )

    assert response.status_code == 400
    assert "paciente" in response.data
    responsavel.refresh_from_db()
    assert responsavel.paciente_id == origem.pk


def test_atualizacao_do_mesmo_paciente_continua_permitida():
    user = FonoFactory()
    paciente = PacienteFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=user)
    responsavel = ResponsavelFactory(paciente=paciente, eh_responsavel_legal_principal=False)
    client = APIClient()
    client.force_authenticate(user)

    response = client.patch(
        f"/api/v1/responsaveis/{responsavel.pk}/",
        {"paciente": str(paciente.pk), "telefone_cifrado": "telefone sintetico"},
        format="json",
    )

    assert response.status_code == 200
    responsavel.refresh_from_db()
    assert responsavel.paciente_id == paciente.pk
    assert responsavel.telefone_cifrado == "telefone sintetico"
