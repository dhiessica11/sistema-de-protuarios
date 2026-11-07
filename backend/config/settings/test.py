"""Test settings - rapido e isolado. Usa SQLite in-memory por padrao."""

import os

# Defaults ANTES de importar base (base le DATABASE_URL)
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-nao-usar-em-prod")
os.environ.setdefault("DJANGO_DEBUG", "False")
os.environ.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")

from .base import *  # noqa: F403, E402

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
# SQLite nao suporta ATOMIC_REQUESTS do mesmo jeito; relaxa p/ teste
DATABASES["default"]["ATOMIC_REQUESTS"] = False  # noqa: F405
# Testes de templates não exigem collectstatic nem manifesto de produção.
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}  # noqa: F405
