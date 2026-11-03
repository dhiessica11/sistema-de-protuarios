"""
Campos Django que cifram transparentemente usando apps.core.encryption.

Uso:
    class Paciente(models.Model):
        cpf = EncryptedCharField(max_length=14, key="A")
        obs_sensivel = EncryptedTextField(key="B")

Limitacoes:
  - Nao da pra buscar por campo cifrado (filter(cpf=X) nao funciona)
  - Para busca determinista (CPF unico), use HashedField em paralelo
"""

from __future__ import annotations

from django.db import models

from apps.core.encryption import KeyName, decrypt, encrypt


class EncryptedCharField(models.TextField):
    """CharField cifrado - internamente TEXT porque ciphertext > plaintext."""

    description = "Campo texto cifrado com chave app-level"

    def __init__(self, *args, key: KeyName = "A", **kwargs):
        self.key_name = key
        # ignoramos max_length (vem do uso em UI/validacao)
        kwargs.pop("max_length", None)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["key"] = self.key_name
        return name, path, args, kwargs

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        return decrypt(value, self.key_name)

    def to_python(self, value):
        return value  # ja vem decifrado via from_db_value

    def get_prep_value(self, value):
        if value is None or value == "":
            return value
        return encrypt(str(value), self.key_name)


class EncryptedTextField(EncryptedCharField):
    """Alias semantico. Mesma implementacao."""

    pass


class HashedField(models.CharField):
    """
    Hash SHA-256 deterministico de um valor sensivel.

    Uso: campo-companheiro de EncryptedCharField quando precisa buscar
    (ex: CPF cifrado + cpf_hash para unique/lookup).
    """

    description = "Hash SHA-256 para busca deterministica"

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 64)
        kwargs.setdefault("db_index", True)
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        # Hash feito explicitamente no save() do model, nao aqui.
        return getattr(model_instance, self.attname)
