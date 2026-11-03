"""
Serializers DRF - validacao de regras de negocio ANTES de persistir.
"""

from rest_framework import serializers

from apps.core.validators import validar_cpf, validar_data_nascimento

from .models import (
    Clinica,
    Consentimento,
    Paciente,
    PacienteEquipe,
    Responsavel,
    Usuario,
)


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


class PacienteSerializer(serializers.ModelSerializer):
    idade = serializers.IntegerField(read_only=True)
    eh_menor = serializers.BooleanField(read_only=True)
    nome_apresentacao = serializers.SerializerMethodField()
    cpf = serializers.CharField(write_only=True, required=False, allow_blank=True)

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

    def get_nome_apresentacao(self, obj):
        return obj.nome_social or obj.nome_civil

    def validate_cpf(self, value):
        if value:
            validar_cpf(value)
        return value

    def validate_data_nascimento(self, value):
        validar_data_nascimento(value)
        return value

    def create(self, validated_data):
        cpf = validated_data.pop("cpf", "")
        instance = super().create(validated_data)
        if cpf:
            instance.cpf_cifrado = cpf
            instance.save()
        return instance


class ResponsavelSerializer(serializers.ModelSerializer):
    cpf = serializers.CharField(write_only=True)
    nome = serializers.CharField(write_only=True)

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
        )
        read_only_fields = ("id", "criado_em")

    def validate_cpf(self, value):
        validar_cpf(value)
        return value

    def validate(self, attrs):
        # Trocar responsavel legal principal exige descricao do comprovante arquivado
        # (upload real desabilitado ate Lote 5 - ver model)
        if attrs.get("eh_responsavel_legal_principal"):
            paciente = attrs.get("paciente")
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

    def create(self, validated_data):
        nome = validated_data.pop("nome")
        cpf = validated_data.pop("cpf")
        instance = Responsavel(**validated_data)
        instance.nome_cifrado = nome
        instance.cpf_cifrado = cpf
        instance.save()
        return instance


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
