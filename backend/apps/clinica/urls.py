from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register("clinicas", views.ClinicaViewSet)
router.register("usuarios", views.UsuarioViewSet)
router.register("pacientes", views.PacienteViewSet, basename="paciente")
router.register("responsaveis", views.ResponsavelViewSet, basename="responsavel")
router.register("consentimentos", views.ConsentimentoViewSet, basename="consentimento")
router.register("paciente-equipe", views.PacienteEquipeViewSet, basename="paciente-equipe")

urlpatterns = router.urls
