"""
Gera chaves A, B, C, E para desenvolvimento local.

SO use este script em DEV. Em prod, chaves vem da cerimonia formal
(ver docs: Bloco 5 - Gap 5.9).

Usa apenas stdlib do Python - NAO precisa de PyNaCl instalado.

Uso:
    cd prontuario-ed/
    python scripts/generate_dev_keys.py
"""
import secrets
from pathlib import Path

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "secrets_dev"
KEYS = ["a", "b", "c", "e", "f"]  # F = HMAC de CPF (nao cifra)
KEY_SIZE = 32  # SecretBox.KEY_SIZE


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    for name in KEYS:
        path = OUTPUT_DIR / f"key_{name}.bin"
        if path.exists():
            print(f"[skip] {path} ja existe - nao sobrescrevi")
            continue
        key = secrets.token_bytes(KEY_SIZE)
        path.write_bytes(key)
        try:
            path.chmod(0o600)
        except (OSError, NotImplementedError):
            pass  # Windows nao suporta chmod completo
        print(f"[ok]   {path} gerada ({len(key)} bytes)")
    print()
    print("ATENCAO: estas chaves sao SO para dev local.")
    print("Nunca commite em git. .gitignore ja protege ./secrets_dev/")


if __name__ == "__main__":
    main()
