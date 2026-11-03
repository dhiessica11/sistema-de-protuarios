"""
Models core da clinica.

Entidades deste modulo:
  - Usuario (login por username, custom)
  - Clinica (metadados da instalacao)
  - Paciente (dados Art. 12 CFFa 777)
  - Responsavel (vinculo legal com paciente menor)
  - Consentimento (versionado, LGPD)
  - PacienteEquipe (quais profissionais atendem o paciente)
"""

import uuid
from datetime import date

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models

from apps.core.fields import EncryptedCharField, EncryptedTextField, HashedField
from apps.core.models import AuditedModel, TimestampedModel, UUIDModel
from apps.core.validators import (
    hash_cpf,
    idade_em_anos,
    normalizar_cpf,
    validar_crfa,
    validar_data_nascimento,
)

# -----------------------------------------------------------------------------
# USUARIO
# -----------------------------------------------------------------------------


class TipoUsuario(models.TextChoices):
    FONO = "fono", "Fonoaudiologo(a)"
    TO = "to", "Terapeuta Ocupacional"
    PSICO = "psico", "Psicologo(a)"
    ADMIN = "admin", "Administrador(a)"
    TI = "ti", "TI (Dhiessica/suporte)"


class MetodoDoisFatores(models.TextChoices):
    TOTP = "totp", "Aplicativo TOTP"
    GOVBR = "govbr", "Gov.br (v0.5+)"
    YUBIKEY = "yubikey", "YubiKey WebAuthn"


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, username, password, **extra_fields):
        if not username:
            raise ValueError("Username obrigatorio")
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(username, password, **extra_fields)

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("tipo", TipoUsuario.TI)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser precisa is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser precisa is_superuser=True")
        return self._create_user(username, password, **extra_fields)


class Usuario(AbstractUser):
    """
    Usuario customizado - login por username.

    Email eh opcional (colaborador pode nao ter).
    Para profissionais clinicos, nome e registro profissional sao bloqueados
    para auto-edicao (so admin altera - ver ADR-004).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("E-mail", blank=True)  # opcional

    tipo = models.CharField(
        "Tipo de usuario",
        max_length=10,
        choices=TipoUsuario.choices,
        default=TipoUsuario.FONO,
    )

    # Registros profissionais (so para profissionais clinicos)
    crfa = models.CharField("CRFa", max_length=20, blank=True, validators=[validar_crfa])
    crp = models.CharField("CRP", max_length=20, blank=True)
    crefito = models.CharField("CREFITO", max_length=20, blank=True)

    # CPF - cifrado + hash para busca
    cpf_cifrado = EncryptedCharField(key="A", blank=True)
    cpf_hash = HashedField(unique=True, null=True, blank=True)

    # 2FA
    metodo_2fa = models.CharField(
        max_length=10,
        choices=MetodoDoisFatores.choices,
        default=MetodoDoisFatores.TOTP,
    )
    totp_secret_cifrado = EncryptedCharField(key="E", blank=True)
    yubikey_registrada = models.BooleanField(default=False)

    # Bloqueio de conta
    tentativas_falhas = models.PositiveSmallIntegerField(default=0)
    conta_bloqueada = models.BooleanField(default=False)
    bloqueada_em = models.DateTimeField(null=True, blank=True)

    # Origem do cadastro
    criado_via = models.CharField(
        max_length=20,
        choices=[("manual", "Manual"), ("convite", "Convite")],
        default="manual",
    )

    objects = UsuarioManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = []  # email removido do required

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def save(self, *args, **kwargs):
        if self.cpf_cifrado:
            # Hash e normalizacao implicitos
            limpo = (
                normalizar_cpf(self.cpf_cifrado)
                if len(self.cpf_cifrado) <= 14
                else self.cpf_cifrado
            )
            if len(limpo) == 11:
                self.cpf_hash = hash_cpf(limpo)
        super().save(*args, **kwargs)

    @property
    def eh_profissional_clinico(self) -> bool:
        return self.tipo in {TipoUsuario.FONO, TipoUsuario.TO, TipoUsuario.PSICO}

    @property
    def eh_admin(self) -> bool:
        return self.tipo == TipoUsuario.ADMIN

    def __str__(self):
        return f"{self.username} ({self.get_tipo_display()})"


# -----------------------------------------------------------------------------
# CLINICA
# -----------------------------------------------------------------------------


class Clinica(UUIDModel, TimestampedModel):
    """
    Metadados da instalacao. Single-tenant: 1 registro esperado.
    """

    nome = models.CharField(max_length=200)
    cnpj = models.CharField(max_length=18, blank=True)
    endereco = models.TextField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    email_atendimento = models.EmailField(blank=True)
    horario_funcionamento = models.JSONField(
        default=dict,
        help_text='{"seg": ["08:00", "20:00"], ...}',
    )

    class Meta:
        verbose_name = "Clinica"
        verbose_name_plural = "Clinicas"

    def __str__(self):
        return self.nome


# -----------------------------------------------------------------------------
# PACIENTE
# -----------------------------------------------------------------------------


class SexoBiologico(models.TextChoices):
    FEMININO = "F", "Feminino"
    MASCULINO = "M", "Masculino"
    OUTRO = "O", "Outro"


class StatusPaciente(models.TextChoices):
    ATIVO = "ativo", "Ativo"
    PAUSADO = "pausado", "Pausado"
    ACOMPANHAMENTO_EXTERNO = "externo", "Em acompanhamento externo"
    ENCERRADO = "encerrado", "Encerrado"
    OBITO = "obito", "Obito"


class Paciente(AuditedModel):
    """
    Paciente da clinica. Art. 12 CFFa 777/2025.
    """

    clinica = models.ForeignKey(Clinica, on_delete=models.PROTECT, related_name="pacientes")

    numero_prontuario = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        help_text="Formato ED-AAAA-NNNN",
    )

    # Dados pessoais - CPF/nome cifrados
    nome_civil = EncryptedCharField(key="A", max_length=200)
    nome_social = EncryptedCharField(key="A", max_length=200, blank=True)
    cpf_cifrado = EncryptedCharField(key="A", blank=True)
    cpf_hash = HashedField(unique=True, null=True, blank=True)
    data_nascimento = models.DateField(validators=[validar_data_nascimento])
    sexo = models.CharField(max_length=1, choices=SexoBiologico.choices)

    # Filiacao
    nome_mae_cifrado = EncryptedCharField(key="A", max_length=200, blank=True)
    nome_pai_cifrado = EncryptedCharField(key="A", max_length=200, blank=True)

    # Origem
    nacionalidade = models.CharField(max_length=50, default="Brasileira")
    naturalidade = models.CharField(max_length=100, blank=True)

    # Contato (do responsavel, geralmente)
    endereco_cifrado = EncryptedCharField(key="A", max_length=500, blank=True)
    telefone_cifrado = EncryptedCharField(key="A", max_length=20, blank=True)

    status = models.CharField(
        max_length=20,
        choices=StatusPaciente.choices,
        default=StatusPaciente.ATIVO,
    )
    data_encerramento = models.DateField(null=True, blank=True)

    class Meta:
        verbose_name = "Paciente"
        verbose_name_plural = "Pacientes"
        indexes = [
            models.Index(fields=["clinica", "status"]),
            models.Index(fields=["numero_prontuario"]),
        ]

    def save(self, *args, **kwargs):
        if self.cpf_cifrado:
            limpo = (
                normalizar_cpf(self.cpf_cifrado)
                if len(self.cpf_cifrado) <= 14
                else self.cpf_cifrado
            )
            if len(limpo) == 11:
                self.cpf_hash = hash_cpf(limpo)
        if not self.numero_prontuario:
            self.numero_prontuario = self._gerar_numero_prontuario()
        super().save(*args, **kwargs)

    def _gerar_numero_prontuario(self) -> str:
        ano = date.today().year
        prefixo = f"ED-{ano}-"
        ultimo = (
            Paciente.objects.filter(numero_prontuario__startswith=prefixo)
            .order_by("-numero_prontuario")
            .first()
        )
        if ultimo:
            seq = int(ultimo.numero_prontuario.split("-")[-1]) + 1
        else:
            seq = 1
        return f"{prefixo}{seq:04d}"

    @property
    def idade(self) -> int:
        return idade_em_anos(self.data_nascimento)

    @property
    def eh_menor(self) -> bool:
        return self.idade < 18

    def __str__(self):
        return f"{self.numero_prontuario} - {self.nome_civil}"


# -----------------------------------------------------------------------------
# RESPONSAVEL
# -----------------------------------------------------------------------------


class VinculoResponsavel(models.TextChoices):
    MAE = "mae", "Mae"
    PAI = "pai", "Pai"
    GUARDIAO = "guardiao", "Guardiao legal"
    OUTRO = "outro", "Outro"


class Responsavel(AuditedModel):
    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name="responsaveis")

    nome_cifrado = EncryptedCharField(key="A", max_length=200)
    cpf_cifrado = EncryptedCharField(key="A")
    cpf_hash = HashedField()  # NAO unique - mesmo CPF pode ter varios filhos

    vinculo = models.CharField(max_length=20, choices=VinculoResponsavel.choices)

    telefone_cifrado = EncryptedCharField(key="A", max_length=20, blank=True)
    email = models.EmailField(blank=True)  # usado para portal

    guarda_compartilhada = models.BooleanField(default=False)
    eh_responsavel_legal_principal = models.BooleanField(
        default=True,
        help_text="Quem assina legalmente. Troca requer comprovante.",
    )

    # Upload de comprovante DESABILITADO ate implementacao do pipeline seguro
    # (Lote 5: ClamAV + MIME real + UUID rename + URL assinada + bucket isolado).
    # Enquanto nao, troca de responsavel legal exige procedimento OFFLINE:
    # comprovante entregue fisicamente/por e-mail cifrado + admin registra em
    # nota operacional (fora deste model).
    comprovante_vinculo_pendente = models.TextField(
        blank=True,
        help_text=(
            "DESABILITADO - upload sera implementado no Lote 5. "
            "Por enquanto, descreva aqui onde o comprovante foi arquivado "
            "fisicamente (ex: 'Pasta Rosanita 2027-11', 'E-mail de 02/11/2027')."
        ),
    )

    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Responsavel"
        verbose_name_plural = "Responsaveis"
        constraints = [
            # So 1 responsavel principal ativo por paciente
            models.UniqueConstraint(
                fields=["paciente"],
                condition=models.Q(eh_responsavel_legal_principal=True, ativo=True),
                name="unico_responsavel_principal_ativo",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.cpf_cifrado:
            limpo = (
                normalizar_cpf(self.cpf_cifrado)
                if len(self.cpf_cifrado) <= 14
                else self.cpf_cifrado
            )
            if len(limpo) == 11:
                self.cpf_hash = hash_cpf(limpo)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nome_cifrado} ({self.get_vinculo_display()})"


# -----------------------------------------------------------------------------
# JUSTIFICATIVAS DE ALTERACAO CADASTRAL
# -----------------------------------------------------------------------------


class AlteracaoCadastral(UUIDModel):
    """Justificativa de identificacao; sem endpoint e sem valores antigos/novos."""

    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name="alteracoes")
    responsavel = models.ForeignKey(
        Responsavel, on_delete=models.PROTECT, null=True, blank=True, related_name="alteracoes"
    )
    autor = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name="alteracoes_cadastrais"
    )
    criado_em = models.DateTimeField(auto_now_add=True)
    campos = models.JSONField()
    justificativa = EncryptedTextField(key="B")


# -----------------------------------------------------------------------------
# CONSENTIMENTO LGPD (VERSIONADO)
# -----------------------------------------------------------------------------


class TipoConsentimento(models.TextChoices):
    LGPD_GERAL = "lgpd_geral", "LGPD - Tratamento de dados do paciente"
    TELEATENDIMENTO = "tele", "Autorizacao de teleatendimento"
    GRAVACAO = "gravacao", "Autorizacao de gravacao de sessao"
    COMPARTILHAMENTO_EQUIPE = "equipe", "Compartilhamento com equipe multidisciplinar"


class Consentimento(UUIDModel, TimestampedModel):
    """
    Consentimento LGPD - versionado.

    Toda alteracao gera NOVO registro. O anterior fica como historico.
    Nunca editado.
    """

    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name="consentimentos")
    responsavel = models.ForeignKey(
        Responsavel, on_delete=models.PROTECT, related_name="consentimentos"
    )
    tipo = models.CharField(max_length=30, choices=TipoConsentimento.choices)
    versao = models.PositiveIntegerField(default=1)

    texto_apresentado = models.TextField(help_text="Texto exato que o responsavel leu ao consentir")
    aceito = models.BooleanField(default=False)
    aceito_em = models.DateTimeField(null=True, blank=True)
    ip_aceite = models.GenericIPAddressField(null=True, blank=True)
    user_agent_aceite = models.TextField(blank=True)

    revogado = models.BooleanField(default=False)
    revogado_em = models.DateTimeField(null=True, blank=True)
    motivo_revogacao = models.TextField(blank=True)

    class Meta:
        verbose_name = "Consentimento"
        verbose_name_plural = "Consentimentos"
        indexes = [
            models.Index(fields=["paciente", "tipo", "-criado_em"]),
        ]

    def clean(self):
        if self.revogado and not self.revogado_em:
            raise ValidationError("Revogacao requer timestamp")
        if self.aceito and not self.aceito_em:
            raise ValidationError("Aceite requer timestamp")

    def __str__(self):
        return f"{self.paciente} - {self.get_tipo_display()} v{self.versao}"


# -----------------------------------------------------------------------------
# PACIENTE x EQUIPE
# -----------------------------------------------------------------------------


class PacienteEquipe(AuditedModel):
    """
    Quais profissionais atendem o paciente.

    Base para permissao de visualizacao:
    - Profissional so ve pacientes onde esta ativo em PacienteEquipe
    - Admin ve tudo
    """

    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name="equipe")
    profissional = models.ForeignKey(
        Usuario, on_delete=models.PROTECT, related_name="pacientes_atendidos"
    )
    desde = models.DateField(auto_now_add=True)
    ate = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)

    motivo_saida = models.TextField(blank=True)

    class Meta:
        verbose_name = "Vinculo Paciente-Equipe"
        verbose_name_plural = "Vinculos Paciente-Equipe"
        constraints = [
            models.UniqueConstraint(
                fields=["paciente", "profissional"],
                condition=models.Q(ativo=True),
                name="unico_vinculo_ativo",
            ),
        ]

    def clean(self):
        if not self.profissional.eh_profissional_clinico:
            raise ValidationError("So profissional clinico (fono/to/psico) pode ser vinculado")

    def __str__(self):
        return f"{self.paciente} <- {self.profissional}"


class TipoRegistro(models.TextChoices):
    EVOLUCAO = "evolucao", "Evolucao"
    RETIFICACAO = "retificacao", "Retificacao"
    ADENDO = "adendo", "Adendo"


class Registro(UUIDModel):
    """Registro clinico. Categoria e autor sao definidos pelo servidor."""

    paciente = models.ForeignKey(Paciente, on_delete=models.PROTECT, related_name="registros")
    autor = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="registros")
    categoria = models.CharField(max_length=10, choices=TipoUsuario.choices)
    tipo = models.CharField(
        max_length=12, choices=TipoRegistro.choices, default=TipoRegistro.EVOLUCAO
    )
    origem = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="derivados"
    )
    justificativa = EncryptedTextField(key="A", blank=True)
    contato_validacao = EncryptedTextField(key="A", blank=True)
    resumo = EncryptedTextField(key="A", blank=True)
    detalhe = EncryptedTextField(key="A")
    compartilhado = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(tipo=TipoRegistro.EVOLUCAO, origem__isnull=True)
                    | models.Q(
                        tipo__in=[TipoRegistro.RETIFICACAO, TipoRegistro.ADENDO],
                        origem__isnull=False,
                    )
                ),
                name="registro_origem_conforme_tipo",
            ),
            models.CheckConstraint(
                condition=~models.Q(tipo=TipoRegistro.RETIFICACAO) | ~models.Q(justificativa=""),
                name="registro_retificacao_justificada",
            ),
            models.CheckConstraint(
                condition=~models.Q(tipo=TipoRegistro.RETIFICACAO)
                | ~models.Q(contato_validacao=""),
                name="registro_retificacao_com_contato",
            ),
        ]
