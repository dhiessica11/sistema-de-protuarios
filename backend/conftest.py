"""Pytest config - garante chaves dev geradas antes dos testes."""

from pathlib import Path

from nacl.secret import SecretBox
from nacl.utils import random


def pytest_configure(config):
    """Gera chaves dev se nao existirem (CI-friendly)."""
    secrets_dir = Path(__file__).resolve().parent.parent / "secrets_dev"
    secrets_dir.mkdir(exist_ok=True)
    for name in ["a", "b", "c", "e", "f"]:
        path = secrets_dir / f"key_{name}.bin"
        if not path.exists():
            path.write_bytes(random(SecretBox.KEY_SIZE))
