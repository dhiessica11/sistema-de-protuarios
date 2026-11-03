"""
Models abstratos reutilizaveis.
"""

import uuid

from django.conf import settings
from django.db import models


class TimestampedModel(models.Model):
    criado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class AuditedModel(UUIDModel, TimestampedModel):
    """
    Base para dados operacionais que registram autoria da ultima modificacao.

    NAO USE para registros clinicos - para esses, autor_id eh IMUTAVEL
    e vai no proprio REGISTRO (modelado no Lote 3).
    """

    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        verbose_name="Criado por",
    )
    atualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
        verbose_name="Atualizado por",
    )

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deletado_em__isnull=True)

    def dead(self):
        return self.filter(deletado_em__isnull=False)


class SoftDeleteModel(models.Model):
    """
    Soft delete para dados OPERACIONAIS (template, nota, pausa).

    PROIBIDO usar em dados clinicos (CFFa 777 guarda permanente).
    """

    deletado_em = models.DateTimeField(null=True, blank=True, db_index=True)
    deletado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="+",
        null=True,
        blank=True,
    )

    objects = SoftDeleteQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False, user=None):
        from django.utils import timezone

        self.deletado_em = timezone.now()
        if user:
            self.deletado_por = user
        self.save(update_fields=["deletado_em", "deletado_por"])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)
