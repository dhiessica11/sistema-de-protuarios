# ADR-006 — Wrapper proprio sobre PyNaCl para cifra multi-chave

**Data:** 2026-11-02
**Status:** Aceita

## Contexto

Projeto exige 5 chaves separadas (A/B/C/D/E) por tipo de dado. Bibliotecas Django de cifra prontas (`django-cryptography-5`, `django-encrypted-fields`) assumem UMA chave global.

## Decisao

Wrapper proprio em `apps/core/encryption.py` + `apps/core/fields.py`.

- `EncryptedCharField(key="A")` escolhe a chave por campo
- Formato armazenado: `base64(nonce || ciphertext)` com XSalsa20-Poly1305
- Chaves em Docker secrets em prod, arquivos em `secrets_dev/` em dev

## Consequencias

- 80 linhas de codigo proprio (manutencao: minima - PyNaCl eh estavel)
- Busca por campo cifrado inviavel - usar HashedField paralelo
- Rotacao de chave implica rebuild total da coluna (procedimento anual)
