"""Dev settings — local development only."""

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Placeholder: INSTALLED_APPS += ["django_extensions"] se precisar

INTERNAL_IPS = ["127.0.0.1"]

# CORS liberado para dev
CORS_ALLOW_ALL_ORIGINS = True

# E-mail no console (sem SMTP real em dev)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Celery sincrono em dev (opcional - comentar se quiser testar async)
# CELERY_TASK_ALWAYS_EAGER = True

# Interface de validação, indisponível por padrão nos demais ambientes.
WEB_CONSULTA_HABILITADA = True
LOGIN_REDIRECT_URL = "web-inicio"

# Acesso administrativo clínico para dados exclusivamente fictícios neste ambiente.
ADMIN_CLINICO_DADOS_FICTICIOS = True
