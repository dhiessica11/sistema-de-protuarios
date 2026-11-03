# ADR-002 — Cifra app-level com PyNaCl

**Data:** 2026-10-24
**Status:** Aceita

## Contexto

Dados sensíveis (CPF, nome civil, registros clínicos, anexos) precisam estar cifrados em repouso. Alternativas: cifra do próprio Postgres (TDE), cifra de disco (LUKS), cifra app-level.

## Decisão

**Cifra app-level com PyNaCl (libsodium)**. Dados sensíveis são cifrados em Python antes de persistir, decifrados na leitura.

5 chaves separadas:
- A — dados operacionais
- B — log de auditoria sensível
- C — gravações de teleatendimento (v1+)
- D — backup client-side (par age)
- E — TOTP secrets

Todas as chaves em **Docker secrets**, nunca em env var.

## Alternativas rejeitadas

- **TDE do Postgres:** Postgres não tem TDE nativo (requer extensões pagas)
- **LUKS no disco:** protege contra roubo físico, não protege se alguém tiver SSH
- **Env var:** aparece em `ps aux`, `cat /proc/*/environ`, dumps de memória, logs de erro

## Consequências

- Backup já sai cifrado do app (duas camadas: app + age)
- Queries por campo cifrado exigem cifra determinística ou busca em memória
- Rotação de chave implica re-cifra total (procedimento anual, janela de madrugada)
- Perda de chave = perda de dados (escrow em cofre físico é obrigatório)
