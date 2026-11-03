"""Garantias de privacidade e autoria da API de Registro."""

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
from apps.clinica.models import Registro, TipoUsuario

pytestmark = pytest.mark.django_db


@pytest.fixture
def contexto():
    paciente = PacienteFactory()
    autor, to = FonoFactory(), TOFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=autor)
    PacienteEquipeFactory(paciente=paciente, profissional=to)
    return paciente, autor, to


def cliente(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.mark.parametrize(
    "categoria_autor,categoria_leitor",
    [
        (TipoUsuario.FONO, TipoUsuario.TO),
        (TipoUsuario.FONO, TipoUsuario.PSICO),
        (TipoUsuario.TO, TipoUsuario.FONO),
        (TipoUsuario.TO, TipoUsuario.PSICO),
        (TipoUsuario.PSICO, TipoUsuario.FONO),
        (TipoUsuario.PSICO, TipoUsuario.TO),
    ],
)
def test_detalhe_nao_vaza_entre_categorias(categoria_autor, categoria_leitor):
    paciente = PacienteFactory()
    autor = UsuarioFactory(tipo=categoria_autor)
    leitor = UsuarioFactory(tipo=categoria_leitor)
    PacienteEquipeFactory(paciente=paciente, profissional=leitor)
    registro = Registro.objects.create(
        paciente=paciente,
        autor=autor,
        categoria=autor.tipo,
        resumo="Resumo sintetico",
        detalhe="Detalhe secreto",
        compartilhado=True,
    )
    resposta = cliente(leitor).get(f"/api/v1/registros/{registro.pk}/")
    assert resposta.status_code == 200
    assert resposta.data["resumo"] == "Resumo sintetico"
    assert "detalhe" not in resposta.data


def test_categoria_diferente_recebe_apenas_resumo_compartilhado(contexto):
    paciente, autor, to = contexto
    privado = Registro.objects.create(
        paciente=paciente,
        autor=autor,
        categoria=autor.tipo,
        resumo="Resumo privado",
        detalhe="segredo privado",
    )
    compartilhado = Registro.objects.create(
        paciente=paciente,
        autor=autor,
        categoria=autor.tipo,
        resumo="Resumo liberado",
        detalhe="segredo clinico",
        compartilhado=True,
    )
    client = cliente(to)
    lista = client.get("/api/v1/registros/")
    assert lista.status_code == 200
    assert lista.data["count"] == 1
    assert lista.data["results"][0]["id"] == str(compartilhado.pk)
    assert lista.data["results"][0]["resumo"] == "Resumo liberado"
    assert "detalhe" not in lista.data["results"][0]
    assert client.get(f"/api/v1/registros/{privado.pk}/").status_code == 404
    detalhe = client.get(f"/api/v1/registros/{compartilhado.pk}/")
    assert detalhe.status_code == 200 and "detalhe" not in detalhe.data
    proprio = cliente(autor).get(f"/api/v1/registros/{compartilhado.pk}/")
    assert proprio.data["detalhe"] == "segredo clinico"
    colega = FonoFactory()
    PacienteEquipeFactory(paciente=paciente, profissional=colega)
    assert (
        cliente(colega).get(f"/api/v1/registros/{privado.pk}/").data["detalhe"] == "segredo privado"
    )


def test_texto_clinico_e_armazenado_cifrado(contexto):
    paciente, autor, _ = contexto
    Registro.objects.create(
        paciente=paciente, autor=autor, categoria=autor.tipo, detalhe="texto clinico sintetico"
    )
    with connection.cursor() as cursor:
        cursor.execute("SELECT detalhe FROM clinica_registro")
        armazenado = cursor.fetchone()[0]
    assert "texto clinico sintetico" not in armazenado


def test_sem_vinculo_e_admin_nao_leem(contexto):
    paciente, autor, _ = contexto
    registro = Registro.objects.create(
        paciente=paciente, autor=autor, categoria=autor.tipo, detalhe="privado"
    )
    assert cliente(FonoFactory()).get(f"/api/v1/registros/{registro.pk}/").status_code == 404
    sem_vinculo = cliente(FonoFactory())
    assert (
        sem_vinculo.post(
            "/api/v1/registros/",
            {"paciente": str(paciente.pk), "detalhe": "nao autorizado"},
            format="json",
        ).status_code
        == 400
    )
    assert Registro.objects.count() == 1
    assert cliente(AdminFactory()).get(f"/api/v1/registros/{registro.pk}/").status_code == 403
    assert APIClient().get("/api/v1/registros/").status_code in (401, 403)
    paciente.equipe.filter(profissional=autor).update(ativo=False)
    assert cliente(autor).get(f"/api/v1/registros/{registro.pk}/").status_code == 404
    autor.is_active = False
    autor.save(update_fields=["is_active"])
    assert cliente(autor).get(f"/api/v1/registros/{registro.pk}/").status_code == 403


def test_autor_e_categoria_sao_definidos_pelo_servidor(contexto):
    paciente, autor, to = contexto
    client = cliente(autor)
    payload = {"paciente": str(paciente.pk), "detalhe": "Evolucao sintetica"}
    resposta = client.post("/api/v1/registros/", payload, format="json")
    assert resposta.status_code == 201
    registro = Registro.objects.get(pk=resposta.data["id"])
    assert registro.autor_id == autor.pk and registro.categoria == autor.tipo
    assert (
        client.post(
            "/api/v1/registros/", {**payload, "autor": str(to.pk)}, format="json"
        ).status_code
        == 400
    )
    assert (
        client.post(
            "/api/v1/registros/", {**payload, "categoria": to.tipo}, format="json"
        ).status_code
        == 400
    )
    assert (
        client.patch(
            f"/api/v1/registros/{registro.pk}/", {"autor": str(to.pk)}, format="json"
        ).status_code
        == 405
    )
    assert client.delete(f"/api/v1/registros/{registro.pk}/").status_code == 405
    categoria_original = registro.categoria
    autor.tipo = TipoUsuario.TO
    autor.save(update_fields=["tipo"])
    registro.refresh_from_db()
    assert registro.categoria == categoria_original
    assert client.get(f"/api/v1/registros/{registro.pk}/").status_code == 404


def test_autoria_imutavel_via_sql_postgresql(contexto):
    if connection.vendor != "postgresql":
        pytest.skip("Exige PostgreSQL")
    paciente, autor, to = contexto
    registro = Registro.objects.create(
        paciente=paciente, autor=autor, categoria=autor.tipo, detalhe="privado"
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        Registro.objects.filter(pk=registro.pk).update(autor=to)
    registro.refresh_from_db()
    assert registro.autor_id == autor.pk
    with pytest.raises(DatabaseError), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE clinica_registro SET autor_id = %s WHERE id = %s", [to.pk, registro.pk]
            )
    registro.refresh_from_db()
    assert registro.autor_id == autor.pk
    with pytest.raises(DatabaseError), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE clinica_registro SET categoria = %s WHERE id = %s", [to.tipo, registro.pk]
            )
    registro.refresh_from_db()
    assert registro.categoria == autor.tipo
    outro_paciente = PacienteFactory(clinica=paciente.clinica)
    with pytest.raises(DatabaseError), transaction.atomic():
        Registro.objects.filter(pk=registro.pk).update(paciente=outro_paciente)
    registro.refresh_from_db()
    assert registro.paciente_id == paciente.pk


def test_conteudo_e_exclusao_protegidos_no_postgresql(contexto):
    if connection.vendor != "postgresql":
        pytest.skip("Exige PostgreSQL")
    paciente, autor, _ = contexto
    registro = Registro.objects.create(
        paciente=paciente, autor=autor, categoria=autor.tipo, detalhe="Texto original"
    )
    with pytest.raises(DatabaseError), transaction.atomic():
        Registro.objects.filter(pk=registro.pk).update(detalhe="texto adulterado")
    with pytest.raises(DatabaseError), transaction.atomic():
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM clinica_registro WHERE id = %s", [registro.pk])
    registro.refresh_from_db()
    assert registro.detalhe == "Texto original"
