"""
Serializers DRF - validacao de regras de negocio ANTES de persistir.
"""

from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import APIException

from apps.core.validators import normalizar_cpf, validar_cpf, validar_data_nascimento

from .cadastro_permissions import validar_campos_de_escrita
from .models import (
    AlteracaoCadastral,
    Clinica,
    Consentimento,
    Paciente,
    PacienteEquipe,
    Responsavel,
    Usuario,
)
from .permissions import admin_clinico_teste


class UsuarioSerializer(serializers.ModelSerializer):
    """Representacao segura - nunca expoe password, totp_secret, cpf."""

    class Meta:
        model = Usuario
        fields = (
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
            "tipo",
            "crfa",
            "crp",
            "crefito",
            "is_active",
            "date_joined",
        )
        read_only_fields = ("id", "date_joined", "crfa", "crp", "crefito")


class ClinicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Clinica
        fields = "__all__"
        read_only_fields = ("id", "criado_em", "atualizado_em")


class CadastroDesatualizado(APIException):
    status_code = 409
    default_detail = (
        "O cadastro foi alterado desde a abertura. Recarregue os dados antes de salvar."
    )
    default_code = "cadastro_desatualizado"


class CadastroProtegidoSerializer(serializers.ModelSerializer):
    justificativa_alteracao = serializers.CharField(
        write_only=True, required=False, min_length=10, max_length=2000
    )
    versao_esperada = serializers.DateTimeField(write_only=True, required=False)
    campos_atualizacao_clinico = frozenset()

    def to_internal_value(self, data):
        validar_campos_de_escrita(self, data)
        return super().to_internal_value(data)

    def campos_identificacao_alterados(self, attrs):
        if self.instance is None:
            return []
        alterados = []
        for fonte, publico in self.campos_identificacao.items():
            if fonte not in attrs:
                continue
            atual = getattr(self.instance, fonte)
            if fonte == "cpf_cifrado":
                atual = normalizar_cpf(atual)
            if attrs[fonte] != atual:
                alterados.append(publico)
        return sorted(alterados)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.campos_identificacao_alterados(attrs) and not attrs.get("justificativa_alteracao"):
            raise serializers.ValidationError(
                {"justificativa_alteracao": "Alteracao de identificacao exige justificativa."}
            )
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        # Revalida sobre a linha atual sob lock: um snapshot antigo nao pode
        # dispensar justificativa nem sobrescrever campos de outro perfil.
        instance = self.Meta.model.objects.select_for_update().get(pk=instance.pk)
        self.instance = instance
        esperada = validated_data.pop("versao_esperada", None)
        if esperada is not None and instance.atualizado_em != esperada:
            raise CadastroDesatualizado()
        validated_data = self.validate(validated_data)
        campos = self.campos_identificacao_alterados(validated_data)
        justificativa = validated_data.pop("justificativa_alteracao", None)
        if "cpf_cifrado" in validated_data and not validated_data["cpf_cifrado"]:
            instance.cpf_hash = None
        instance = super().update(instance, validated_data)
        if campos:
            responsavel = instance if isinstance(instance, Responsavel) else None
            AlteracaoCadastral.objects.create(
                paciente=responsavel.paciente if responsavel else instance,
                responsavel=responsavel,
                autor=self.context["request"].user,
                campos=campos,
                justificativa=justificativa,
            )
        return instance


class PacienteSerializer(CadastroProtegidoSerializer):
    campos_criacao_admin = frozenset(
        {
            "clinica",
            "nome_civil",
            "nome_social",
            "cpf",
            "data_nascimento",
            "sexo",
            "nacionalidade",
            "naturalidade",
            "endereco_cifrado",
            "telefone_cifrado",
        }
    )
    campos_atualizacao_admin = campos_criacao_admin | {"justificativa_alteracao", "versao_esperada"}
    campos_atualizacao_clinico = frozenset({"nome_social", "status", "data_encerramento"})
    campos_identificacao = {
        "nome_civil": "nome_civil",
        "cpf_cifrado": "cpf",
        "data_nascimento": "data_nascimento",
        "sexo": "sexo",
        "nacionalidade": "nacionalidade",
        "naturalidade": "naturalidade",
    }
    idade = serializers.IntegerField(read_only=True)
    eh_menor = serializers.BooleanField(read_only=True)
    nome_apresentacao = serializers.SerializerMethodField()
    cpf = serializers.CharField(
        source="cpf_cifrado", write_only=True, required=False, allow_blank=True
    )

    class Meta:
        model = Paciente
        fields = (
            "id",
            "numero_prontuario",
            "clinica",
            "nome_civil",
            "nome_social",
            "nome_apresentacao",
            "cpf",
            "data_nascimento",
            "idade",
            "eh_menor",
            "sexo",
            "nacionalidade",
            "naturalidade",
            "endereco_cifrado",
            "telefone_cifrado",
            "status",
            "data_encerramento",
            "criado_em",
            "atualizado_em",
            "justificativa_alteracao",
            "versao_esperada",
        )
        read_only_fields = (
            "id",
            "numero_prontuario",
            "criado_em",
            "atualizado_em",
            "idade",
            "eh_menor",
            "nome_apresentacao",
        )

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request and admin_clinico_teste(request.user):
            fields["cpf"].write_only = False
        return fields

    def get_nome_apresentacao(self, obj):
        return obj.nome_social or obj.nome_civil

    def validate_cpf(self, value):
        if value:
            validar_cpf(value)
        return normalizar_cpf(value) if value else value

    def validate_data_nascimento(self, value):
        validar_data_nascimento(value)
        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if self.instance is not None and "clinica" in attrs:
            if attrs["clinica"].pk != self.instance.clinica_id:
                raise serializers.ValidationError({"clinica": "Clinica do paciente e imutavel."})
        return attrs


class ResponsavelSerializer(CadastroProtegidoSerializer):
    campos_criacao_admin = frozenset(
        {
            "paciente",
            "nome",
            "cpf",
            "vinculo",
            "telefone_cifrado",
            "email",
            "guarda_compartilhada",
            "eh_responsavel_legal_principal",
            "comprovante_vinculo_pendente",
            "ativo",
        }
    )
    campos_atualizacao_admin = campos_criacao_admin | {"justificativa_alteracao", "versao_esperada"}
    campos_identificacao = {"nome_cifrado": "nome", "cpf_cifrado": "cpf"}
    cpf = serializers.CharField(source="cpf_cifrado", write_only=True)
    nome = serializers.CharField(source="nome_cifrado", write_only=True, max_length=200)

    class Meta:
        model = Responsavel
        fields = (
            "id",
            "paciente",
            "nome",
            "cpf",
            "vinculo",
            "telefone_cifrado",
            "email",
            "guarda_compartilhada",
            "eh_responsavel_legal_principal",
            "comprovante_vinculo_pendente",
            "ativo",
            "criado_em",
            "atualizado_em",
            "justificativa_alteracao",
            "versao_esperada",
        )
        read_only_fields = ("id", "criado_em", "atualizado_em")

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request and admin_clinico_teste(request.user):
            fields["cpf"].write_only = False
            fields["nome"].write_only = False
        return fields

    def validate_cpf(self, value):
        validar_cpf(value)
        return normalizar_cpf(value)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        # O vinculo historico pertence ao paciente original. Para outro paciente,
        # o cadastro deve ser criado pelo fluxo administrativo, sem mover este.
        if self.instance is not None:
            paciente = attrs.get("paciente", self.instance.paciente)
            if paciente.pk != self.instance.paciente_id:
                raise serializers.ValidationError(
                    {"paciente": "Nao e permitido alterar o paciente de um responsavel existente."}
                )

        # Trocar responsavel legal principal exige descricao do comprovante arquivado
        # (upload real desabilitado ate Lote 5 - ver model)
        if attrs.get("eh_responsavel_legal_principal"):
            paciente = attrs.get("paciente", self.instance.paciente if self.instance else None)
            existe_outro = (
                Responsavel.objects.filter(
                    paciente=paciente,
                    eh_responsavel_legal_principal=True,
                    ativo=True,
                )
                .exclude(pk=self.instance.pk if self.instance else None)
                .exists()
            )
            if existe_outro and not attrs.get("comprovante_vinculo_pendente"):
                raise serializers.ValidationError(
                    {
                        "comprovante_vinculo_pendente": (
                            "Troca de responsavel legal principal exige descricao "
                            "do comprovante arquivado offline (upload sera implementado "
                            "no Lote 5 com pipeline seguro)."
                        )
                    }
                )
        return attrs


class ConsentimentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consentimento
        fields = (
            "id",
            "paciente",
            "responsavel",
            "tipo",
            "versao",
            "texto_apresentado",
            "aceito",
            "aceito_em",
            "revogado",
            "revogado_em",
            "motivo_revogacao",
            "criado_em",
        )
        read_only_fields = ("id", "versao", "criado_em")

    def validate(self, attrs):
        """
        Valida que:
        1. Responsavel realmente pertence ao paciente informado
        2. Profissional nao-admin so cria para pacientes do seu escopo
        """
        paciente = attrs.get("paciente")
        responsavel = attrs.get("responsavel")

        if responsavel and paciente and responsavel.paciente_id != paciente.id:
            raise serializers.ValidationError(
                {
                    "responsavel": "Responsavel nao pertence ao paciente informado.",
                }
            )

        request = self.context.get("request")
        if request and request.user.is_authenticated:
            user = request.user
            if not user.eh_admin and user.eh_profissional_clinico:
                # Profissional so cria consentimento para pacientes da sua equipe
                vinculado = paciente.equipe.filter(profissional=user, ativo=True).exists()
                if not vinculado:
                    raise serializers.ValidationError(
                        {
                            "paciente": "Paciente fora do seu escopo de atendimento.",
                        }
                    )

        return attrs

    def create(self, validated_data):
        paciente = validated_data["paciente"]
        tipo = validated_data["tipo"]
        ultima = (
            Consentimento.objects.filter(paciente=paciente, tipo=tipo).order_by("-versao").first()
        )
        validated_data["versao"] = (ultima.versao + 1) if ultima else 1
        return super().create(validated_data)

    def update(self, instance, validated_data):
        raise serializers.ValidationError(
            "Consentimento eh versionado - crie novo em vez de editar."
        )


class PacienteEquipeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PacienteEquipe
        fields = (
            "id",
            "paciente",
            "profissional",
            "desde",
            "ate",
            "ativo",
            "motivo_saida",
            "criado_em",
        )
        read_only_fields = ("id", "desde", "criado_em")

    def validate_profissional(self, value):
        if not value.eh_profissional_clinico:
            raise serializers.ValidationError("So fono, TO ou psico pode compor equipe clinica.")
        return value
