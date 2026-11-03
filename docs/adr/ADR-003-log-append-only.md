# ADR-003 — Log de auditoria append-only via trigger Postgres

**Data:** 2026-10-24
**Status:** Aceita

## Contexto

LGPD Art. 46-49 + CFFa 777 exigem log de auditoria à prova de adulteração. Bug de aplicação, acesso privilegiado, ou admin malicioso NÃO podem apagar nem alterar o log.

## Decisão

Tabela `log_auditoria` com:

1. **Permissão Postgres nega** UPDATE e DELETE a qualquer role (incluindo o owner da aplicação)
2. **Hash encadeado SHA-256:** `hash_atual = SHA256(conteudo || hash_anterior)`
3. **Trigger valida hash** na inserção; INSERT com hash inconsistente falha
4. **Job diário** verifica a cadeia inteira e alerta se quebrada
5. **Retenção permanente** — nunca apaga
6. **Valores sensíveis cifrados** com chave B (separada da chave A dos dados)

Implementação só por trigger PG, não só por convenção de código.

## Alternativas rejeitadas

- **Log em arquivo:** fácil de apagar, difícil de buscar
- **Log em outro banco:** complexidade adicional, mesmo risco se admin acessa
- **Append-only "por convenção":** um `UPDATE` do admin bypassa tudo
- **Hash sem cadeia:** adulteração de uma linha não detectável sem comparar com cópia

## Consequências

- Admin da aplicação NÃO consegue apagar log mesmo via Django ORM
- Migração que precisar mexer no log precisa de DBA + justificativa + nova trigger
- Cada registro clínico gera 1+ linhas no log
- Volume estimado em 5 anos: ~500MB (aceitável)
