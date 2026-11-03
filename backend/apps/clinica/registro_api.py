"""API clinica com acesso restrito a equipe e categoria."""

from collections.abc import Mapping

from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Paciente, Registro
from .permissions import IsProfissionalClinico


class RegistroSerializer(serializers.ModelSerializer):
    paciente = serializers.PrimaryKeyRelatedField(queryset=Paciente.objects.all())

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        user = getattr(request, "user", None)
        fields["paciente"].queryset = (
            Paciente.objects.filter(equipe__profissional=user, equipe__ativo=True).distinct()
            if user and user.is_authenticated
            else Paciente.objects.none()
        )
        return fields

    class Meta:
        model = Registro
        fields = (
            "id",
            "paciente",
            "autor",
            "categoria",
            "resumo",
            "detalhe",
            "compartilhado",
            "criado_em",
        )
        read_only_fields = ("id", "autor", "categoria", "criado_em")

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            return super().to_internal_value(data)
        proibidos = set(data) - {"paciente", "resumo", "detalhe", "compartilhado"}
        if proibidos:
            raise ValidationError({campo: "Campo nao permitido." for campo in sorted(proibidos)})
        return super().to_internal_value(data)

    def validate_paciente(self, paciente):
        if not paciente.equipe.filter(
            profissional=self.context["request"].user, ativo=True
        ).exists():
            raise PermissionDenied("Paciente fora do escopo.")
        return paciente

    def to_representation(self, obj):
        if obj.categoria == self.context["request"].user.tipo:
            return super().to_representation(obj)
        return {
            "id": str(obj.pk),
            "paciente": str(obj.paciente_id),
            "autor": str(obj.autor_id),
            "categoria": obj.categoria,
            "resumo": obj.resumo,
            "compartilhado": obj.compartilhado,
            "criado_em": self.fields["criado_em"].to_representation(obj.criado_em),
        }


class RegistroViewSet(viewsets.ModelViewSet):
    serializer_class = RegistroSerializer
    permission_classes = [IsProfissionalClinico]
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        return (
            Registro.objects.filter(
                paciente__equipe__profissional=user, paciente__equipe__ativo=True
            )
            .filter(Q(categoria=user.tipo) | Q(compartilhado=True))
            .defer("detalhe")
            .order_by("criado_em", "id")
            .distinct()
        )

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user, categoria=self.request.user.tipo)
