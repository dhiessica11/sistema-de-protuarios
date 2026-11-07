"""Planos fono de teste: somente revisões aprovadas e correntes."""

from uuid import UUID

from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import serializers, viewsets
from rest_framework.exceptions import ValidationError

from .avaliacao_fono_api import FonoEmTeste
from .correcao_teste import bloquear_e_validar_correcao, validar_paciente_correcao
from .models import (
    AvaliacaoFono,
    DificuldadeFono,
    ItemPlanoFono,
    Paciente,
    PlanoFono,
    RevisaoObjetivoFono,
)
from .permissions import admin_clinico_teste


class ItemEntradaSerializer(serializers.Serializer):
    revisao = serializers.UUIDField()
    meta = serializers.CharField(max_length=2000, allow_blank=False)

    def to_internal_value(self, data):
        if hasattr(data, "keys") and set(data) != {"revisao", "meta"}:
            raise ValidationError("Informe apenas revisão e meta.")
        return super().to_internal_value(data)


class ItemPlanoSerializer(serializers.ModelSerializer):
    objetivo = serializers.CharField(source="revisao.texto", read_only=True)
    dificuldade = serializers.CharField(source="revisao.dificuldade.descricao", read_only=True)

    class Meta:
        model = ItemPlanoFono
        fields = ("id", "revisao", "objetivo", "dificuldade", "meta")


class PlanoSerializer(serializers.ModelSerializer):
    paciente = serializers.PrimaryKeyRelatedField(queryset=Paciente.objects.none())
    corrige = serializers.PrimaryKeyRelatedField(
        queryset=PlanoFono.objects.none(), allow_null=True, required=False
    )
    corrigido = serializers.SerializerMethodField()
    itens = ItemPlanoSerializer(many=True, read_only=True)
    itens_informados = ItemEntradaSerializer(
        many=True, write_only=True, allow_empty=False, max_length=50
    )
    recursos = serializers.CharField(max_length=5000, allow_blank=True, required=False)
    orientacoes = serializers.CharField(max_length=5000, allow_blank=True, required=False)
    estado_assinatura = serializers.SerializerMethodField()

    class Meta:
        model = PlanoFono
        fields = (
            "id",
            "paciente",
            "autor",
            "corrige",
            "corrigido",
            "inicio",
            "fim",
            "recursos",
            "orientacoes",
            "itens",
            "itens_informados",
            "estado_assinatura",
            "criado_em",
        )
        read_only_fields = ("id", "autor", "criado_em")

    def get_corrigido(self, obj):
        return PlanoFono.objects.filter(corrige_id=obj.pk).exists()

    def get_estado_assinatura(self, obj):
        return "sem_assinatura"

    def get_fields(self):
        fields = super().get_fields()
        user = self.context["request"].user
        fields["paciente"].queryset = (
            Paciente.objects.all()
            if admin_clinico_teste(user)
            else Paciente.objects.filter(equipe__profissional=user, equipe__ativo=True).distinct()
        )
        fields["corrige"].queryset = (
            PlanoFono.objects.all()
            if admin_clinico_teste(user)
            else PlanoFono.objects.filter(
                paciente__equipe__profissional=user, paciente__equipe__ativo=True
            ).distinct()
        )
        return fields

    def to_internal_value(self, data):
        allowed = {
            "paciente",
            "corrige",
            "inicio",
            "fim",
            "recursos",
            "orientacoes",
            "itens_informados",
        }
        if hasattr(data, "keys") and set(data) - allowed:
            raise ValidationError({"detail": "Foram informados campos não permitidos."})
        return super().to_internal_value(data)

    def validate(self, attrs):
        if attrs["fim"] < attrs["inicio"]:
            raise ValidationError({"fim": "A data final deve ser igual ou posterior à inicial."})
        ids = [item["revisao"] for item in attrs["itens_informados"]]
        if len(ids) != len(set(ids)):
            raise ValidationError({"itens_informados": "Não repita a mesma revisão."})
        return validar_paciente_correcao(attrs)

    @transaction.atomic
    def create(self, validated_data):
        bloquear_e_validar_correcao(PlanoFono, validated_data.get("corrige"))
        itens = validated_data.pop("itens_informados")
        ids = [item["revisao"] for item in itens]
        paciente = validated_data["paciente"]
        revisoes = list(
            RevisaoObjetivoFono.objects.filter(
                pk__in=ids, dificuldade__avaliacao__paciente=paciente
            ).select_related("dificuldade")
        )
        dificuldades = [r.dificuldade_id for r in revisoes]
        if len(revisoes) != len(ids) or len(dificuldades) != len(set(dificuldades)):
            raise ValidationError(
                {"itens_informados": "Revisões inválidas ou duplicadas para este paciente."}
            )
        # Bloqueia avaliações antes das dificuldades, na mesma ordem das revisões.
        avaliacoes = {r.dificuldade.avaliacao_id for r in revisoes}
        list(AvaliacaoFono.objects.filter(pk__in=avaliacoes).order_by("id").select_for_update())
        # Revisões também bloqueiam a dificuldade: a decisão não pode mudar entre a verificação e a gravação.
        list(DificuldadeFono.objects.filter(pk__in=dificuldades).order_by("id").select_for_update())
        for revisao in revisoes:
            if AvaliacaoFono.objects.filter(corrige_id=revisao.dificuldade.avaliacao_id).exists():
                raise ValidationError(
                    {
                        "itens_informados": "A avaliação foi corrigida; use objetivos da versão mais recente."
                    }
                )
            ultima = (
                RevisaoObjetivoFono.objects.filter(dificuldade_id=revisao.dificuldade_id)
                .order_by("-criado_em", "-id")
                .first()
            )
            if not ultima or ultima.pk != revisao.pk or ultima.decisao != "aprovado":
                raise ValidationError(
                    {
                        "itens_informados": "Use somente a revisão mais recente e aprovada de cada dificuldade."
                    }
                )
        plano = PlanoFono.objects.create(**validated_data)
        for item in itens:
            ItemPlanoFono.objects.create(plano=plano, revisao_id=item["revisao"], meta=item["meta"])
        return plano


@method_decorator(never_cache, name="dispatch")
class PlanoViewSet(viewsets.ModelViewSet):
    permission_classes = [FonoEmTeste]
    serializer_class = PlanoSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        planos = PlanoFono.objects.all()
        if not admin_clinico_teste(self.request.user):
            planos = planos.filter(
                paciente__equipe__profissional=self.request.user, paciente__equipe__ativo=True
            )
        return (
            planos.prefetch_related("itens__revisao__dificuldade")
            .order_by("-criado_em", "-id")
            .distinct()
        )

    def list(self, request, *args, **kwargs):
        try:
            self.paciente_id = UUID(request.query_params.get("paciente", ""))
        except ValueError as exc:
            raise ValidationError({"paciente": "Informe um paciente válido."}) from exc
        return super().list(request, *args, **kwargs)

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        return (
            queryset.filter(paciente_id=self.paciente_id)
            if hasattr(self, "paciente_id")
            else queryset
        )

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)
