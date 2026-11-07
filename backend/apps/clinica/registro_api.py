"""API clinica com acesso restrito a equipe e categoria."""

from collections.abc import Mapping
from uuid import UUID

from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Paciente, Registro, TipoRegistro
from .permissions import IsProfissionalClinico, admin_clinico_teste


class RegistroSerializer(serializers.ModelSerializer):
    paciente = serializers.PrimaryKeyRelatedField(queryset=Paciente.objects.all())
    origem = serializers.PrimaryKeyRelatedField(
        queryset=Registro.objects.none(), required=False, allow_null=True
    )
    contato_validacao = serializers.CharField(required=False, allow_blank=True, max_length=200)
    estado_assinatura = serializers.SerializerMethodField()
    categoria_simulada = serializers.ChoiceField(
        choices=["fono", "to", "psico"], required=False, write_only=True
    )

    def get_estado_assinatura(self, obj):
        # Ainda nao ha integracao nem evidencia de assinatura verificavel.
        return "sem_assinatura"

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if user and admin_clinico_teste(user):
            fields["paciente"].queryset = Paciente.objects.all()
            fields["origem"].queryset = Registro.objects.all()
            return fields
        fields["paciente"].queryset = (
            Paciente.objects.filter(equipe__profissional=user, equipe__ativo=True).distinct()
            if user and user.is_authenticated
            else Paciente.objects.none()
        )
        fields["origem"].queryset = (
            Registro.objects.filter(
                categoria=user.tipo,
                paciente__equipe__profissional=user,
                paciente__equipe__ativo=True,
            ).distinct()
            if user and user.is_authenticated and user.is_active
            else Registro.objects.none()
        )
        return fields

    class Meta:
        model = Registro
        fields = (
            "id",
            "paciente",
            "autor",
            "categoria",
            "categoria_simulada",
            "tipo",
            "origem",
            "justificativa",
            "contato_validacao",
            "resumo",
            "detalhe",
            "compartilhado",
            "estado_assinatura",
            "criado_em",
        )
        read_only_fields = ("id", "autor", "categoria", "criado_em")

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)
        proibidos = set(data) - {
            "paciente",
            "resumo",
            "detalhe",
            "compartilhado",
            "tipo",
            "origem",
            "justificativa",
            "contato_validacao",
            "categoria_simulada",
        }
        if proibidos:
            raise ValidationError({campo: "Campo nao permitido." for campo in sorted(proibidos)})
        return super().to_internal_value(data)

    def validate_paciente(self, paciente):
        if admin_clinico_teste(self.context["request"].user):
            return paciente
        if not paciente.equipe.filter(
            profissional=self.context["request"].user, ativo=True
        ).exists():
            raise PermissionDenied("Paciente fora do escopo.")
        return paciente

    def validate(self, attrs):
        attrs = super().validate(attrs)
        tipo = attrs.get("tipo", TipoRegistro.EVOLUCAO)
        origem = attrs.get("origem")
        categoria_simulada = attrs.get("categoria_simulada")
        if not admin_clinico_teste(self.context["request"].user) and categoria_simulada:
            raise ValidationError(
                {"categoria_simulada": "Campo disponível apenas para testes administrativos."}
            )
        if admin_clinico_teste(self.context["request"].user):
            if not origem and not categoria_simulada:
                raise ValidationError(
                    {"categoria_simulada": "Informe a categoria simulada do registro fictício."}
                )
            if origem and categoria_simulada and categoria_simulada != origem.categoria:
                raise ValidationError(
                    {"categoria_simulada": "A categoria deve ser a mesma da origem."}
                )
        if tipo == TipoRegistro.EVOLUCAO and origem is not None:
            raise ValidationError({"origem": "Evolucao nao deve apontar para outro registro."})
        if tipo in (TipoRegistro.RETIFICACAO, TipoRegistro.ADENDO):
            if origem is None:
                raise ValidationError({"origem": "Informe o registro original."})
            if origem.paciente_id != attrs["paciente"].pk:
                raise ValidationError({"origem": "Registro original pertence a outro paciente."})
        if tipo == TipoRegistro.RETIFICACAO and len(attrs.get("justificativa", "").strip()) < 50:
            raise ValidationError(
                {"justificativa": "Retificacao exige justificativa de pelo menos 50 caracteres."}
            )
        if tipo == TipoRegistro.RETIFICACAO and not attrs.get("contato_validacao", "").strip():
            raise ValidationError(
                {"contato_validacao": "Informe quem foi contatado para validacao."}
            )
        return attrs

    def to_representation(self, obj):
        if obj.categoria == self.context["request"].user.tipo or admin_clinico_teste(
            self.context["request"].user
        ):
            privados = {"detalhe", "justificativa", "contato_validacao"}
            if obj.get_deferred_fields() & privados:
                obj.refresh_from_db(fields=sorted(privados))
            return super().to_representation(obj)
        return {
            "id": str(obj.pk),
            "paciente": str(obj.paciente_id),
            "autor": str(obj.autor_id),
            "categoria": obj.categoria,
            "tipo": obj.tipo,
            "resumo": obj.resumo,
            "compartilhado": obj.compartilhado,
            "estado_assinatura": "sem_assinatura",
            "criado_em": self.fields["criado_em"].to_representation(obj.criado_em),
        }


class RegistroViewSet(viewsets.ModelViewSet):
    serializer_class = RegistroSerializer

    def get_permissions(self):
        if admin_clinico_teste(self.request.user):
            return []
        return [IsProfissionalClinico()]

    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        registros = Registro.objects.all()
        if not admin_clinico_teste(user):
            registros = registros.filter(
                paciente__equipe__profissional=user, paciente__equipe__ativo=True
            ).filter(Q(categoria=user.tipo) | Q(compartilhado=True))
        registros = (
            registros.defer("detalhe", "justificativa", "contato_validacao")
            .order_by("criado_em", "id")
            .distinct()
        )
        paciente = self.request.query_params.get("paciente")
        if paciente is not None:
            try:
                paciente = UUID(paciente)
            except (ValueError, TypeError, AttributeError) as exc:
                raise ValidationError({"paciente": "Identificador inválido."}) from exc
            registros = registros.filter(paciente_id=paciente)
        return registros

    def perform_create(self, serializer):
        # O domínio simulado não altera a autoria real da conta administrativa.
        simulada = serializer.validated_data.pop("categoria_simulada", None)
        if admin_clinico_teste(self.request.user):
            origem = serializer.validated_data.get("origem")
            categoria = origem.categoria if origem else simulada
        else:
            categoria = self.request.user.tipo
        serializer.save(autor=self.request.user, categoria=categoria)
