from django.urls import path
from rest_framework.routers import DefaultRouter

from . import views
from .avaliacao_fono_api import AvaliacaoViewSet, RevisaoViewSet
from .plano_fono_api import PlanoViewSet
from .registro_api import RegistroViewSet

router = DefaultRouter()
router.register("clinicas", views.ClinicaViewSet)
router.register("usuarios", views.UsuarioViewSet)
router.register("pacientes", views.PacienteViewSet, basename="paciente")
router.register("responsaveis", views.ResponsavelViewSet, basename="responsavel")
router.register("consentimentos", views.ConsentimentoViewSet, basename="consentimento")
router.register("paciente-equipe", views.PacienteEquipeViewSet, basename="paciente-equipe")


router.register("registros", RegistroViewSet, basename="registro")

router.register("avaliacoes-fono", AvaliacaoViewSet, basename="avaliacao-fono")
router.register("planos-fono", PlanoViewSet, basename="plano-fono")

urlpatterns = [
    path(
        "dificuldades-fono/<uuid:dificuldade_pk>/revisoes/",
        RevisaoViewSet.as_view({"post": "create"}),
        name="revisao-fono",
    )
] + router.urls
