"""
Cifra app-level com PyNaCl SecretBox (XSalsa20-Poly1305 autenticado).

6 chaves separadas por proposito:
  A - dados operacionais (CPF, nome, endereco)
  B - log de auditoria sensivel
  C - gravacoes de teleatendimento (v1+)
  D - backup client-side (par age - handled separadamente, nao aqui)
  E - TOTP secrets
  F - HMAC de CPF para busca determinista (NAO cifra - usada em HMAC)

Chaves vem de Docker secrets em prod. Em dev, de arquivos em ./secrets_dev/.

Formato cifrado armazenado: base64(nonce || ciphertext).
Nonce aleatorio por operacao (24 bytes).

NUNCA logue a chave. NUNCA passe a chave pela rede.
"""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Literal

from django.conf import settings
from nacl.exceptions import CryptoError
from nacl.secret import SecretBox
from nacl.utils import random as nacl_random

KeyName = Literal["A", "B", "C", "E", "F"]


class EncryptionError(Exception):
    """Falha ao cifrar/decifrar - deve explodir, nunca engolir."""


class _KeyRegistry:
    """Cache de chaves carregadas. Evita I/O a cada operacao."""

    _cache: dict[str, bytes] = {}

    @classmethod
    def get(cls, name: KeyName) -> bytes:
        if name not in cls._cache:
            cls._cache[name] = cls._load(name)
        return cls._cache[name]

    @classmethod
    def _load(cls, name: KeyName) -> bytes:
        # Prod: Docker secrets em /run/secrets/
        docker_path = Path(f"/run/secrets/prontuario_key_{name.lower()}")
        if docker_path.exists():
            # Chaves binarias: whitespace tambem pode ser parte dos 32 bytes.
            key = docker_path.read_bytes()
        else:
            # Dev: arquivos em secrets_dev/
            dev_dir = Path(settings.BASE_DIR).parent / "secrets_dev"
            dev_path = dev_dir / f"key_{name.lower()}.bin"
            if not dev_path.exists():
                raise EncryptionError(
                    f"Chave {name} nao encontrada. Rode: python scripts/generate_dev_keys.py"
                )
            key = dev_path.read_bytes()

        if len(key) != SecretBox.KEY_SIZE:
            raise EncryptionError(
                f"Chave {name} tem {len(key)} bytes, esperado {SecretBox.KEY_SIZE}"
            )
        return key

    @classmethod
    def reset(cls) -> None:
        """Usado em testes para forcar reload."""
        cls._cache.clear()


def encrypt(plaintext: str | bytes, key_name: KeyName = "A") -> str:
    """
    Cifra texto plano com a chave indicada.

    Retorna string base64 pronta pra armazenar em CharField/TextField.
    """
    if plaintext is None:
        raise EncryptionError("Nao se cifra None - trate antes")
    if isinstance(plaintext, str):
        plaintext = plaintext.encode("utf-8")

    if key_name == "F":
        raise EncryptionError("Chave F e para HMAC, nao cifra")

    box = SecretBox(_KeyRegistry.get(key_name))
    nonce = nacl_random(SecretBox.NONCE_SIZE)
    ciphertext = box.encrypt(plaintext, nonce)  # inclui nonce no inicio
    return base64.b64encode(ciphertext).decode("ascii")


def decrypt(encoded: str, key_name: KeyName = "A") -> str:
    """
    Decifra string base64 cifrada com encrypt().

    Explode em CryptoError se chave errada ou dado adulterado.
    """
    if not encoded:
        return ""
    if key_name == "F":
        raise EncryptionError("Chave F e para HMAC, nao cifra")
    try:
        box = SecretBox(_KeyRegistry.get(key_name))
        raw = base64.b64decode(encoded.encode("ascii"))
        return box.decrypt(raw).decode("utf-8")
    except (CryptoError, ValueError) as exc:
        raise EncryptionError(f"Falha ao decifrar com chave {key_name}") from exc


def generate_key() -> bytes:
    """Gera chave aleatoria de 32 bytes para SecretBox ou HMAC."""
    return nacl_random(SecretBox.KEY_SIZE)
