"""Registro experimental de tentativas, sem interpretação clínica."""

import json
from datetime import date
from uuid import UUID

from django.http import Http404
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from .avaliacao_fono_api import FonoEmTeste
from .models import ItemPlanoFono, Paciente, SessaoFono


class SessaoSerializer(serializers.ModelSerializer):
    paciente = serializers.PrimaryKeyRelatedField(queryset=Paciente.objects.none())
    objetivo = serializers.PrimaryKeyRelatedField(
        queryset=ItemPlanoFono.objects.none(), required=False, allow_null=True
    )
    atividade = serializers.CharField(max_length=1000, allow_blank=False)
    observacoes = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    tentativas = serializers.ListField(
        child=serializers.ChoiceField(choices=["I", "E", "G", "VP", "VT", "FP", "FT", "VS"]),
        max_length=100,
        allow_empty=True,
        write_only=True,
    )
    objetivo_texto = serializers.CharField(
        source="objetivo.revisao.texto", read_only=True, default=None
    )
    resultados = serializers.SerializerMethodField()
    estado_assinatura = serializers.SerializerMethodField()

    class Meta:
        model = SessaoFono
        fields = (
            "id",
            "paciente",
            "autor",
            "objetivo",
            "objetivo_texto",
            "data",
            "atividade",
            "observacoes",
            "tentativas",
            "resultados",
            "estado_assinatura",
            "criado_em",
        )
        read_only_fields = ("id", "autor", "criado_em")

    def get_fields(self):
        fields = super().get_fields()
        user = self.context["request"].user
        fields["paciente"].queryset = Paciente.objects.filter(
            equipe__profissional=user, equipe__ativo=True
        ).distinct()
        fields["objetivo"].queryset = ItemPlanoFono.objects.filter(
            plano__paciente__equipe__profissional=user, plano__paciente__equipe__ativo=True
        ).distinct()
        return fields

    def to_internal_value(self, data):
        allowed = {"paciente", "objetivo", "data", "atividade", "observacoes", "tentativas"}
        if hasattr(data, "keys") and set(data) - allowed:
            raise ValidationError({"detail": "Foram informados campos não permitidos."})
        return super().to_internal_value(data)

    def validate(self, attrs):
        objetivo = attrs.get("objetivo")
        if objetivo and objetivo.plano.paciente_id != attrs["paciente"].id:
            raise ValidationError({"objetivo": "O objetivo deve pertencer ao mesmo paciente."})
        return attrs

    def create(self, validated_data):
        tentativas = validated_data.pop("tentativas")
        validated_data["tentativas_cifradas"] = json.dumps(
            tentativas, ensure_ascii=True, separators=(",", ":")
        )
        return super().create(validated_data)

    def get_estado_assinatura(self, obj):
        return "sem_assinatura"

    def get_resultados(self, obj):
        tentativas = json.loads(obj.tentativas_cifradas)
        total = len(tentativas)
        contagens = {
            codigo: tentativas.count(codigo)
            for codigo in ("I", "E", "G", "VP", "VT", "FP", "FT", "VS")
        }
        ajuda = total - contagens["I"] - contagens["E"]
        return {
            "tentativas": tentativas,
            "total": total,
            "contagens": contagens,
            "percentual_independente": round(100 * contagens["I"] / total, 2) if total else None,
            "percentual_erro": round(100 * contagens["E"] / total, 2) if total else None,
            "percentual_ajuda": round(100 * ajuda / total, 2) if total else None,
        }


@method_decorator(never_cache, name="dispatch")
class SessaoViewSet(viewsets.ModelViewSet):
    permission_classes = [FonoEmTeste]
    serializer_class = SessaoSerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return (
            SessaoFono.objects.filter(
                paciente__equipe__profissional=self.request.user, paciente__equipe__ativo=True
            )
            .select_related("objetivo__revisao")
            .order_by("-data", "-criado_em", "id")
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

    @action(detail=False, methods=["get"], url_path="evolucao")
    def evolucao(self, request):
        try:
            paciente = UUID(request.query_params.get("paciente", ""))
            objetivo = UUID(request.query_params.get("objetivo", ""))
            inicio = date.fromisoformat(request.query_params.get("inicio", ""))
            fim = date.fromisoformat(request.query_params.get("fim", ""))
        except (ValueError, TypeError) as exc:
            raise ValidationError(
                {"detail": "Informe paciente, objetivo e datas válidas."}
            ) from exc
        if fim < inicio or (fim - inicio).days > 365:
            raise ValidationError({"detail": "Informe um período de até 366 dias."})
        if not ItemPlanoFono.objects.filter(
            pk=objetivo,
            plano__paciente_id=paciente,
            plano__paciente__equipe__profissional=request.user,
            plano__paciente__equipe__ativo=True,
        ).exists():
            raise Http404
        sessoes = list(
            self.get_queryset()
            .filter(paciente_id=paciente, objetivo_id=objetivo, data__range=(inicio, fim))
            .order_by("data", "criado_em", "id")[:1001]
        )
        if len(sessoes) > 1000:
            raise ValidationError(
                {"detail": "Mais de 1000 sessões no período; reduza o intervalo."}
            )
        por_data = {}
        for sessao in sessoes:
            chave = sessao.data.isoformat()
            item = por_data.setdefault(
                chave,
                {
                    "data": chave,
                    "sessoes": 0,
                    "total": 0,
                    "independentes": 0,
                    "erros": 0,
                    "ajudas": 0,
                },
            )
            tentativas = json.loads(sessao.tentativas_cifradas)
            item["sessoes"] += 1
            item["total"] += len(tentativas)
            item["independentes"] += tentativas.count("I")
            item["erros"] += tentativas.count("E")
            item["ajudas"] += sum(codigo not in ("I", "E") for codigo in tentativas)
        pontos = []
        for item in por_data.values():
            total = item["total"]
            for campo in ("independentes", "erros", "ajudas"):
                item[f"percentual_{campo}"] = round(item[campo] * 100 / total, 2) if total else None
            pontos.append(item)
        return Response(
            {
                "inicio": inicio.isoformat(),
                "fim": fim.isoformat(),
                "objetivo": str(objetivo),
                "pontos": pontos,
            }
        )

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)
