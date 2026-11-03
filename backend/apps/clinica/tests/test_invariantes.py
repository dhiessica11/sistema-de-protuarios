"""
Testes de INVARIANTES do dominio.

Esses testes NUNCA podem passar a quebrar silenciosamente.
Cada um garante uma regra de negocio critica (CFFa 777 ou LGPD).
"""

from datetime import date, timedelta

import pytest
from django.contrib import admin as django_admin
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.clinica.factories import (
    AdminFactory,
    ConsentimentoFactory,
    FonoFactory,
    PacienteFactory,
    ResponsavelFactory,
    UsuarioFactory,
)
from apps.clinica.models import (
    Consentimento,
    Paciente,
    PacienteEquipe,
    Responsavel,
)
from apps.core.encryption import EncryptionError, decrypt, encrypt

# -----------------------------------------------------------------------------
# CIFRA
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestCifra:
    def test_encrypt_decrypt_roundtrip(self):
        texto = "Marina Souza"
        cifrado = encrypt(texto, "A")
        assert cifrado != texto
        assert decrypt(cifrado, "A") == texto

    def test_encrypt_de_strings_diferentes_geram_cifras_diferentes(self):
        """Nonce aleatorio por operacao -> mesma string cifra diferente."""
        a = encrypt("segredo", "A")
        b = encrypt("segredo", "A")
        assert a != b
        assert decrypt(a, "A") == decrypt(b, "A") == "segredo"

    def test_decrypt_com_chave_errada_falha(self):
        cifrado = encrypt("segredo", "A")
        with pytest.raises(EncryptionError):
            decrypt(cifrado, "B")


# -----------------------------------------------------------------------------
# USUARIO
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestUsuario:
    def test_login_por_username_nao_email(self):
        """Decisao da Dhi 2026-11-02: colaborador pode nao ter email."""
        user = UsuarioFactory(username="ana_fono", email="")
        assert user.USERNAME_FIELD == "username"
        assert user.email == ""

    def test_fono_eh_profissional_clinico(self):
        user = FonoFactory()
        assert user.eh_profissional_clinico is True
        assert user.eh_admin is False

    def test_admin_eh_admin_nao_clinico(self):
        user = AdminFactory()
        assert user.eh_admin is True
        assert user.eh_profissional_clinico is False


# -----------------------------------------------------------------------------
# PACIENTE
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestPaciente:
    def test_numero_prontuario_gerado_automaticamente(self):
        p = PacienteFactory()
        ano = date.today().year
        assert p.numero_prontuario.startswith(f"ED-{ano}-")
        assert len(p.numero_prontuario.split("-")[-1]) == 4

    def test_numero_prontuario_sequencial(self):
        p1 = PacienteFactory()
        p2 = PacienteFactory()
        n1 = int(p1.numero_prontuario.split("-")[-1])
        n2 = int(p2.numero_prontuario.split("-")[-1])
        assert n2 == n1 + 1

    def test_cpf_cifrado_persistido_e_decifrado_transparente(self):
        p = PacienteFactory(cpf_cifrado="12345678909")
        p.refresh_from_db()
        assert p.cpf_cifrado == "12345678909"

    def test_cpf_hash_usa_hmac_nao_sha_salt(self):
        """
        Hash determinista vem de HMAC(chave_F, cpf), nao SHA256(salt+cpf).
        """
        import hashlib
        import hmac

        from apps.core.encryption import _KeyRegistry
        from apps.core.validators import hash_cpf

        cpf = "12345678909"
        h1 = hash_cpf(cpf)
        h2 = hash_cpf(cpf)
        # Determinista
        assert h1 == h2
        # Realmente HMAC com chave F
        esperado = hmac.new(_KeyRegistry.get("F"), cpf.encode(), hashlib.sha256).hexdigest()
        assert h1 == esperado
        # Nao coincide com SHA256(cpf) direto (sem HMAC)
        assert h1 != hashlib.sha256(cpf.encode()).hexdigest()

    def test_eh_menor_quando_crianca(self):
        hoje = date.today()
        p = PacienteFactory(
            data_nascimento=hoje - timedelta(days=365 * 6)  # 6 anos
        )
        assert p.eh_menor is True

    def test_idade_minima_zero_meses_aceita(self):
        """Regra 6: clinica infantil atende prematuros."""
        from apps.core.validators import validar_data_nascimento

        validar_data_nascimento(date.today())  # bebe nascido hoje

    def test_data_nascimento_futura_rejeitada(self):
        from apps.core.validators import validar_data_nascimento

        with pytest.raises(ValidationError):
            validar_data_nascimento(date.today() + timedelta(days=1))


# -----------------------------------------------------------------------------
# RESPONSAVEL
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestResponsavel:
    def test_um_responsavel_principal_ativo_por_paciente(self):
        paciente = PacienteFactory()
        ResponsavelFactory(
            paciente=paciente,
            eh_responsavel_legal_principal=True,
            ativo=True,
        )
        with pytest.raises(IntegrityError):
            with transaction.atomic():
                Responsavel.objects.create(
                    paciente=paciente,
                    nome_cifrado="Outro",
                    cpf_cifrado="11144477735",
                    vinculo="pai",
                    eh_responsavel_legal_principal=True,
                    ativo=True,
                )

    def test_dois_responsaveis_nao_principais_ok(self):
        """Guarda compartilhada: 2 responsaveis, so 1 'principal'."""
        paciente = PacienteFactory()
        ResponsavelFactory(
            paciente=paciente,
            eh_responsavel_legal_principal=True,
            ativo=True,
        )
        r2 = ResponsavelFactory.build(
            paciente=paciente,
            eh_responsavel_legal_principal=False,
            ativo=True,
        )
        r2.save()  # nao explode


# -----------------------------------------------------------------------------
# CONSENTIMENTO
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestConsentimento:
    def test_versao_1_na_criacao(self):
        c = ConsentimentoFactory()
        assert c.versao == 1


# -----------------------------------------------------------------------------
# PACIENTE x EQUIPE
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestPacienteEquipe:
    def test_so_profissional_clinico_na_equipe(self):
        """Regra: admin nao atende paciente diretamente."""
        paciente = PacienteFactory()
        admin = AdminFactory()
        vinculo = PacienteEquipe(paciente=paciente, profissional=admin)
        with pytest.raises(ValidationError):
            vinculo.full_clean()

    def test_vinculo_fono_ok(self):
        paciente = PacienteFactory()
        fono = FonoFactory()
        vinculo = PacienteEquipe(paciente=paciente, profissional=fono, ativo=True)
        vinculo.full_clean()  # nao explode


# -----------------------------------------------------------------------------
# ADMIN DJANGO BLOQUEADO (ADR-005)
# -----------------------------------------------------------------------------


@pytest.mark.django_db
class TestAdminBloqueado:
    """
    ADR-005: Paciente, Responsavel, Consentimento, PacienteEquipe NAO podem
    estar registrados no Admin - bypassaria validacoes de serializer.
    """

    def test_paciente_nao_registrado_no_admin(self):
        assert not django_admin.site.is_registered(Paciente)

    def test_responsavel_nao_registrado_no_admin(self):
        assert not django_admin.site.is_registered(Responsavel)

    def test_consentimento_nao_registrado_no_admin(self):
        assert not django_admin.site.is_registered(Consentimento)

    def test_paciente_equipe_nao_registrado_no_admin(self):
        assert not django_admin.site.is_registered(PacienteEquipe)
