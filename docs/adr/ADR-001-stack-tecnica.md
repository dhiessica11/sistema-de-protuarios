# ADR-001 — Stack técnica

**Data:** 2026-10-24
**Status:** Aceita

## Contexto

Sistema de prontuário para clínica infantil — single-tenant, self-hosted, LGPD + CFFa 777/2025, ~100 pacientes, 2 fonos. Desenvolvedora solo trabalhando em noites e fins de semana.

## Decisão

**Backend:** Django 5 + DRF + PyNaCl + Celery + Redis.
**Banco:** PostgreSQL 16 (não SQLite — triggers, RLS, permissões).
**Frontend:** React 18 + Vite + TanStack Query + Tailwind.
**Infra:** Docker + docker-compose. VPS nacional (dados em território BR por LGPD).
**Backup:** pg_dump + WAL archiving → MagaluCloud Object Storage (São Paulo, principal) + Locaweb Storage (SP, espelho mensal) + cifra client-side `age` (chave D no cofre). Decisão nov/2026: 100% território nacional, elimina transferência internacional LGPD Art. 33.

## Alternativas rejeitadas

- **SaaS multi-tenant:** overkill, complexidade regulatória maior
- **MySQL/MariaDB:** sem RLS, triggers mais limitadas
- **FastAPI:** menos admin pronto, menos biblioteca de autenticação
- **Node.js:** menos maduro em LGPD/compliance
- **SQLite:** esconde problemas de constraint, trigger e permissão

## Consequências

- Desenvolvedora precisa dominar Django (já domina)
- Postgres local obrigatório desde dia 1 (não há atalho via SQLite)
- Django Admin disponível, mas BLOQUEADO para models clínicos
