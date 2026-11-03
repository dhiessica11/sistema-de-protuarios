"""
Factory boys para testes.

CPFs usam faker pt_BR que gera CPFs validos (passam no digito verificador).
"""

import factory
from factory.django import DjangoModelFactory
from faker import Faker

from .models import (
    Clinica,
    Consentimento,
    Paciente,
    PacienteEquipe,
    Responsavel,
    TipoConsentimento,
    TipoUsuario,
    Usuario,
    VinculoResponsavel,
)

fake = Faker("pt_BR")


class ClinicaFactory(DjangoModelFactory):
    class Meta:
        model = Clinica

    nome = factory.Sequence(lambda n: f"Espaco Desenvolver {n}")
    cnpj = "00.000.000/0001-00"
    endereco = "Rua Teste, 123 - Dourados/MS"


class UsuarioFactory(DjangoModelFactory):
    class Meta:
        model = Usuario

    username = factory.Sequence(lambda n: f"user{n}")
    first_name = factory.LazyAttribute(lambda _: fake.first_name())
    last_name = factory.LazyAttribute(lambda _: fake.last_name())
    tipo = TipoUsuario.FONO
    is_active = True

    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        obj.set_password(extracted or "senha-de-teste-12chars")
        if create:
            obj.save()


class FonoFactory(UsuarioFactory):
    tipo = TipoUsuario.FONO
    crfa = "MS-12345"


class TOFactory(UsuarioFactory):
    tipo = TipoUsuario.TO


class AdminFactory(UsuarioFactory):
    tipo = TipoUsuario.ADMIN


class PacienteFactory(DjangoModelFactory):
    class Meta:
        model = Paciente

    clinica = factory.SubFactory(ClinicaFactory)
    nome_civil = factory.LazyAttribute(lambda _: fake.name())
    # Idade minima 0 meses (fono atua em prematuros - Regra 6)
    data_nascimento = factory.LazyAttribute(
        lambda _: fake.date_of_birth(minimum_age=0, maximum_age=14)
    )
    sexo = "F"
    nacionalidade = "Brasileira"


class ResponsavelFactory(DjangoModelFactory):
    class Meta:
        model = Responsavel

    paciente = factory.SubFactory(PacienteFactory)
    nome_cifrado = factory.LazyAttribute(lambda _: fake.name())
    cpf_cifrado = factory.LazyAttribute(lambda _: fake.cpf())
    vinculo = VinculoResponsavel.MAE
    email = factory.LazyAttribute(lambda _: fake.email())
    eh_responsavel_legal_principal = True
    ativo = True


class ConsentimentoFactory(DjangoModelFactory):
    class Meta:
        model = Consentimento

    paciente = factory.SubFactory(PacienteFactory)
    responsavel = factory.SubFactory(
        ResponsavelFactory,
        paciente=factory.SelfAttribute("..paciente"),
    )
    tipo = TipoConsentimento.LGPD_GERAL
    texto_apresentado = "Texto de teste do consentimento LGPD..."
    aceito = True


class PacienteEquipeFactory(DjangoModelFactory):
    class Meta:
        model = PacienteEquipe

    paciente = factory.SubFactory(PacienteFactory)
    profissional = factory.SubFactory(FonoFactory)
    ativo = True
