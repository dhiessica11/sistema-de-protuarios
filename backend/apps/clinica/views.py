"""
ViewSets DRF.

Autorizacao em apps/clinica/permissions.py.

Regras:
- DELETE bloqueado via http_method_names (retorna 405)
- Permissoes avaliadas por action (get_permissions)
- Admin cadastra/edita identificacao e contatos; profissional vinculado edita
  nome social, status e encerramento do paciente; responsavel e so leitura para clinicos
- Consentimento imutavel apos criacao (so GET/POST)
"""

from rest_framework import viewsets

from .models import (
    Clinica,
    Consentimento,
    Paciente,
    PacienteEquipe,
    Responsavel,
    Usuario,
)
from .permissions import (
    IsAdmin,
    IsAdminOrClinico,
    PacienteNoScopeDoProfissional,
)
from .serializers import (
    ClinicaSerializer,
    ConsentimentoSerializer,
    PacienteEquipeSerializer,
    PacienteSerializer,
    ResponsavelSerializer,
    UsuarioSerializer,
)


class ClinicaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Clinica.objects.all()
    serializer_class = ClinicaSerializer
    permission_classes = [IsAdminOrClinico]


class UsuarioViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Usuario.objects.filter(is_active=True)
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdminOrClinico]


class PacienteViewSet(viewsets.ModelViewSet):
    """
    - Admin: cadastra e altera campos administrativos/identificacao
    - Profissional vinculado: altera nome social/status/encerramento dos seus pacientes
    - DELETE: 405 (http_method_names)
    """

    serializer_class = PacienteSerializer
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [IsAdmin()]  # so admin cria
        return [IsAdminOrClinico(), PacienteNoScopeDoProfissional()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Paciente.objects.none()
        if user.eh_admin:
            return Paciente.objects.all()
        if user.eh_profissional_clinico:
            return Paciente.objects.filter(
                equipe__profissional=user,
                equipe__ativo=True,
            ).distinct()
        return Paciente.objects.none()

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def perform_update(self, serializer):
        serializer.save(atualizado_por=self.request.user)


class ResponsavelViewSet(viewsets.ModelViewSet):
    serializer_class = ResponsavelSerializer
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_permissions(self):
        if self.action == "create":
            return [IsAdmin()]
        return [IsAdminOrClinico(), PacienteNoScopeDoProfissional()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Responsavel.objects.none()
        if user.eh_admin:
            return Responsavel.objects.all()
        if user.eh_profissional_clinico:
            return Responsavel.objects.filter(
                paciente__equipe__profissional=user,
                paciente__equipe__ativo=True,
            ).distinct()
        return Responsavel.objects.none()

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)

    def perform_update(self, serializer):
        serializer.save(atualizado_por=self.request.user)


class ConsentimentoViewSet(viewsets.ModelViewSet):
    """
    Consentimento VERSIONADO - imutavel apos criacao.
    - GET/POST apenas
    - Validacao de escopo (paciente/responsavel) feita no serializer
    """

    serializer_class = ConsentimentoSerializer
    http_method_names = ["get", "post", "head", "options"]
    permission_classes = [IsAdminOrClinico, PacienteNoScopeDoProfissional]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Consentimento.objects.none()
        if user.eh_admin:
            return Consentimento.objects.all()
        return Consentimento.objects.filter(
            paciente__equipe__profissional=user,
            paciente__equipe__ativo=True,
        ).distinct()

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx["request"] = self.request
        return ctx


class PacienteEquipeViewSet(viewsets.ModelViewSet):
    """
    Vinculo paciente-profissional.
    - Admin: cria, altera (sem delete), ve todos
    - Profissional: ve apenas os SEUS vinculos (read-only)
    """

    serializer_class = PacienteEquipeSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [IsAdminOrClinico()]
        return [IsAdmin()]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return PacienteEquipe.objects.none()
        if user.eh_admin:
            return PacienteEquipe.objects.all()
        if user.eh_profissional_clinico:
            return PacienteEquipe.objects.filter(profissional=user)
        return PacienteEquipe.objects.none()

    def perform_create(self, serializer):
        serializer.save(criado_por=self.request.user)
