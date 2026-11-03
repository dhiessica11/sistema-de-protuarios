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
