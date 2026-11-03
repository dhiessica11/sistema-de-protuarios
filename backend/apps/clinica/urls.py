from rest_framework.routers import DefaultRouter

from . import views
from .registro_api import RegistroViewSet

router = DefaultRouter()
router.register("clinicas", views.ClinicaViewSet)
router.register("usuarios", views.UsuarioViewSet)
router.register("pacientes", views.PacienteViewSet, basename="paciente")
router.register("responsaveis", views.ResponsavelViewSet, basename="responsavel")
router.register("consentimentos", views.ConsentimentoViewSet, basename="consentimento")
router.register("paciente-equipe", views.PacienteEquipeViewSet, basename="paciente-equipe")


router.register("registros", RegistroViewSet, basename="registro")

urlpatterns = router.urls
