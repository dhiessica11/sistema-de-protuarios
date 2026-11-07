"""Fluxo experimental de avaliação, sem interpretação de protocolos."""

from django.conf import settings
from django.db import transaction
from django.db.models import Prefetch
from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import serializers, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import BasePermission

from .models import AvaliacaoFono, DificuldadeFono, Paciente, RevisaoObjetivoFono, TipoUsuario


class FonoEmTeste(BasePermission):
    def has_permission(self, request, view):
        if not getattr(settings, "WEB_CONSULTA_HABILITADA", False):
            raise Http404
        return (
            request.user.is_authenticated
            and request.user.is_active
            and request.user.tipo == TipoUsuario.FONO
        )


class RevisaoSerializer(serializers.ModelSerializer):
    def to_internal_value(self, data):
        if hasattr(data, "keys") and set(data) - {"decisao", "texto"}:
            raise ValidationError({"detail": "Foram informados campos não permitidos."})
        return super().to_internal_value(data)

    class Meta:
        model = RevisaoObjetivoFono
        fields = ("id", "autor", "decisao", "texto", "criado_em")
        read_only_fields = ("id", "autor", "criado_em")
        extra_kwargs = {"texto": {"max_length": 2000, "allow_blank": False}}


class DificuldadeSerializer(serializers.ModelSerializer):
    revisoes = RevisaoSerializer(many=True, read_only=True)

    class Meta:
        model = DificuldadeFono
        fields = ("id", "descricao", "proposta", "revisoes")


class AvaliacaoSerializer(serializers.ModelSerializer):
    paciente = serializers.PrimaryKeyRelatedField(queryset=Paciente.objects.none())
    origem = serializers.PrimaryKeyRelatedField(
        queryset=AvaliacaoFono.objects.none(), allow_null=True, required=False
    )
    dificuldades = DificuldadeSerializer(many=True, read_only=True)
    dificuldades_informadas = serializers.ListField(
        child=serializers.CharField(max_length=500, allow_blank=False),
        max_length=50,
        allow_empty=True,
        write_only=True,
    )
    protocolo = serializers.CharField(max_length=200, allow_blank=False)
    observacoes = serializers.CharField(max_length=5000, required=False, allow_blank=True)

    class Meta:
        model = AvaliacaoFono
        fields = (
            "id",
            "paciente",
            "autor",
            "origem",
            "data",
            "protocolo",
            "observacoes",
            "dificuldades",
            "dificuldades_informadas",
            "criado_em",
        )
        read_only_fields = ("id", "autor", "criado_em")

    def get_fields(self):
        fields = super().get_fields()
        user = self.context["request"].user
        fields["paciente"].queryset = Paciente.objects.filter(
            equipe__profissional=user, equipe__ativo=True
        ).distinct()
        fields["origem"].queryset = AvaliacaoFono.objects.filter(
            paciente__equipe__profissional=user, paciente__equipe__ativo=True
        ).distinct()
        return fields

    def to_internal_value(self, data):
        permitidos = {
            "paciente",
            "origem",
            "data",
            "protocolo",
            "observacoes",
            "dificuldades_informadas",
        }
        if hasattr(data, "keys") and set(data) - permitidos:
            raise ValidationError({"detail": "Foram informados campos não permitidos."})
        return super().to_internal_value(data)

    def validate(self, attrs):
        origem = attrs.get("origem")
        if origem and (origem.paciente_id != attrs["paciente"].id or attrs["data"] < origem.data):
            raise ValidationError(
                {"origem": "A origem deve ser do mesmo paciente e não pode ser posterior."}
            )
        if origem and origem.protocolo.casefold() != attrs["protocolo"].casefold():
            raise ValidationError(
                {"protocolo": "A reavaliação deve usar o mesmo protocolo da origem."}
            )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        dificuldades = validated_data.pop("dificuldades_informadas")
        avaliacao = AvaliacaoFono.objects.create(**validated_data)
        for texto in dificuldades:
            DificuldadeFono.objects.create(
                avaliacao=avaliacao, descricao=texto, proposta=f"Definir objetivo para: {texto}"
            )
        return avaliacao


@method_decorator(never_cache, name="dispatch")
class AvaliacaoViewSet(viewsets.ModelViewSet):
    serializer_class = AvaliacaoSerializer
    permission_classes = [FonoEmTeste]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return (
            AvaliacaoFono.objects.filter(
                paciente__equipe__profissional=self.request.user, paciente__equipe__ativo=True
            )
            .prefetch_related(
                Prefetch(
                    "dificuldades",
                    queryset=DificuldadeFono.objects.order_by("criado_em", "id").prefetch_related(
                        Prefetch(
                            "revisoes",
                            queryset=RevisaoObjetivoFono.objects.order_by("criado_em", "id"),
                        )
                    ),
                )
            )
            .order_by("-data", "-criado_em", "id")
            .distinct()
        )

    def list(self, request, *args, **kwargs):
        paciente = request.query_params.get("paciente")
        if not paciente:
            raise ValidationError({"paciente": "Informe o paciente."})
        try:
            from uuid import UUID

            UUID(paciente)
        except ValueError as exc:
            raise ValidationError({"paciente": "Identificador inválido."}) from exc
        self.queryset_paciente = paciente
        return super().list(request, *args, **kwargs)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        if hasattr(self, "queryset_paciente"):
            queryset = queryset.filter(paciente_id=self.queryset_paciente)
        return queryset

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)


@method_decorator(never_cache, name="dispatch")
class RevisaoViewSet(viewsets.ModelViewSet):
    serializer_class = RevisaoSerializer
    permission_classes = [FonoEmTeste]
    http_method_names = ["post", "head", "options"]

    def get_queryset(self):
        return RevisaoObjetivoFono.objects.none()

    @transaction.atomic
    def perform_create(self, serializer):
        dificuldade = DificuldadeFono.objects.filter(
            pk=self.kwargs["dificuldade_pk"],
            avaliacao__paciente__equipe__profissional=self.request.user,
            avaliacao__paciente__equipe__ativo=True,
        ).first()
        if dificuldade is None:
            raise Http404
        dificuldade = DificuldadeFono.objects.select_for_update().get(pk=dificuldade.pk)
        serializer.save(autor=self.request.user, dificuldade=dificuldade)
