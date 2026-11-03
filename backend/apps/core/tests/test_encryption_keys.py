"""Regressao: arquivos de chave sao binarios, sem normalizacao de whitespace."""

from pathlib import Path

import pytest

from apps.core import encryption


@pytest.fixture
def key_paths(tmp_path, monkeypatch, settings):
    docker_dir = tmp_path / "docker-secrets"
    docker_dir.mkdir()
    dev_dir = tmp_path / "secrets_dev"
    dev_dir.mkdir()
    settings.BASE_DIR = tmp_path / "backend"

    def mapped_path(value):
        path = Path(value)
        if path.parent == Path("/run/secrets"):
            return docker_dir / path.name
        return path

    monkeypatch.setattr(encryption, "Path", mapped_path)
    encryption._KeyRegistry.reset()
    yield docker_dir, dev_dir
    encryption._KeyRegistry.reset()


@pytest.mark.parametrize("name", ["A", "B", "C", "E", "F"])
@pytest.mark.parametrize("boundary", [b" ", b"\t", b"\n", b"\r", b"\v", b"\f"])
def test_docker_key_preserves_binary_whitespace(key_paths, name, boundary):
    docker_dir, _ = key_paths
    key = boundary + b"x" * 30 + boundary
    (docker_dir / f"prontuario_key_{name.lower()}").write_bytes(key)

    assert encryption._KeyRegistry.get(name) == key
    if name != "F":
        assert encryption.decrypt(encryption.encrypt("teste", name), name) == "teste"


@pytest.mark.parametrize("key", [b"", b"x" * 31, b"x" * 33, b"x" * 32 + b"\n"])
def test_invalid_docker_key_rejected_without_dev_fallback(key_paths, key):
    docker_dir, dev_dir = key_paths
    (docker_dir / "prontuario_key_a").write_bytes(key)
    (dev_dir / "key_a.bin").write_bytes(b"v" * 32)

    with pytest.raises(encryption.EncryptionError, match="esperado 32"):
        encryption._KeyRegistry.get("A")


def test_dev_key_preserves_binary_whitespace(key_paths):
    _, dev_dir = key_paths
    key = b"\n" + b"x" * 30 + b" "
    (dev_dir / "key_a.bin").write_bytes(key)

    assert encryption._KeyRegistry.get("A") == key
