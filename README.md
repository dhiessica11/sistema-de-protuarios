# Prontuário Eletrônico — Espaço Desenvolver

Sistema de prontuário clínico infantil (fonoaudiologia + TO + psicologia).
Compliance CFFa 777/2025 + LGPD. Single-tenant self-hosted.

**Versão-base:** 0.2.4 (dependências e leitura de chaves corrigidas sobre os Lotes 1 + 2)
**Status:** Em desenvolvimento, nunca rodou em produção. Sobre a v0.2.4: Registro, retificação e adendo em revisão; assinatura ICP-Brasil ainda não implementada.

## Pré-validação

Todos os checks do CI passam localmente:

- Instalação com hashes de `backend/requirements-dev.lock` e projeto sem nova resolução
- `python manage.py makemigrations --check --dry-run` → "No changes detected"
- `ruff check .` → "All checks passed!"
- `ruff format --check .` → "nenhuma alteração necessária"
- `pytest` → todos os testes devem passar

## Requisitos

- Docker Desktop (recomendado) **OU** Python 3.12 + PostgreSQL 16 + Redis 7
- 4GB RAM livre
- Portas livres: 8000 (Django). Postgres e Redis são internos ao Docker.

Dependências: Django 5.2 LTS, DRF 3.18 e PyNaCl 1.6. Instalação e atualização
reproduzíveis em [docs/DEPENDENCIAS.md](docs/DEPENDENCIAS.md). Python 3.13 ainda
não foi validado com este lock.

## Instalação com Docker

```bash
# 1. Entrar na pasta
cd prontuario-ed

# 2. Copiar env e gerar DJANGO_SECRET_KEY
cp .env.example .env
python3 -c "import secrets; print('DJANGO_SECRET_KEY=' + secrets.token_urlsafe(50))"
# cole no .env substituindo a linha

# 3. Gerar chaves de cifra DEV (5 chaves: A/B/C/E/F)
python3 scripts/generate_dev_keys.py

# 4. Build + up
docker compose up --build

# Em outro terminal:
# 5. Aplicar migrations (JÁ ESTÃO VERSIONADAS - nao precisa makemigrations)
docker compose exec web python manage.py migrate

# 6. Superuser
docker compose exec web python manage.py createsuperuser

# 7. Verificar
curl http://localhost:8000/health/
```

Abrir no navegador:
- `http://localhost:8000/` — interface de consulta em desenvolvimento (somente dados fictícios)
- `http://localhost:8000/admin/` — Admin (só gerencia usuários e clínicas)
- `http://localhost:8000/api/v1/` — API browsable

A interface web inicial usa a conta existente e apresenta pacientes conforme o perfil;
profissionais podem consultar os registros acessíveis pela API. A administração não
vê texto clínico, e TI não acessa essa tela. Profissionais de fono vinculados podem
criar avaliações de teste, registrar dificuldades e revisar as propostas geradas.
Reavaliações são vinculadas a uma avaliação anterior do mesmo protocolo. A área de
planejamento permite salvar planos de teste com metas para objetivos aprovados. A
interface ainda não possui cadastro de pacientes, criação de registros clínicos ou assinatura. Ela só está habilitada nas configurações
de desenvolvimento e não autoriza o uso com dados reais. Na rede local de testes,
use o endereço do servidor na porta 8000; não exponha o servidor de desenvolvimento
à internet.

## Rodar os testes

```bash
docker compose exec web pytest -v
# Todos os testes devem passar
```

## Lint

```bash
docker compose exec web ruff check .
docker compose exec web ruff format --check .
```

## Parar

```bash
docker compose down       # mantém dados
docker compose down -v    # apaga banco também (dev only)
```

## Estrutura

```
prontuario-ed/
├── backend/
│   ├── apps/
│   │   ├── core/              # cifra, fields, validators, models base
│   │   └── clinica/
│   │       ├── migrations/    # 0001_initial.py (gerada pelo Django, versionada)
│   │       ├── permissions.py # IsAdmin / IsAdminOrClinico / PacienteNoScopeDoProfissional
│   │       ├── models.py
│   │       ├── serializers.py
│   │       ├── views.py
│   │       └── tests/
│   │           ├── test_invariantes.py       # 22 testes
│   │           └── test_api_permissions.py   # 16 testes
│   ├── config/
│   ├── conftest.py
│   ├── Dockerfile
│   └── pyproject.toml
├── scripts/
│   └── generate_dev_keys.py   # 5 chaves A/B/C/E/F
├── infra/
├── docs/adr/                  # 10 ADRs
├── secrets_dev/               # [gerado, ignorado pelo git]
├── docker-compose.yml
├── .env.example
└── .gitignore
```

## 10 Architecture Decision Records

| ADR | Decisão |
|---|---|
| 001 | Stack: Django 5 + PostgreSQL 16 + React |
| 002 | Cifra app-level com PyNaCl (5 chaves A/B/C/D/E) |
| 003 | Log append-only via trigger PG + hash encadeado |
| 004 | Autoria imutável + retificação cria novo registro |
| 005 | Admin Django bloqueado para dados clínicos |
| 006 | Wrapper próprio PyNaCl (multi-chave) |
| 007 | User model customizado com login por username |
| 008 | 25 regras de negócio decididas em bloco (2026-11-02) |
| 009 | Backup 100% nacional — MagaluCloud + Locaweb (2026-11-02) |
| 010 | Correções pós-review externa — permissões, migrations, HMAC CPF, upload desabilitado (2026-11-02) |

## 5 chaves de cifra

| Chave | Uso | Operação |
|---|---|---|
| A | Dados operacionais (CPF, nome, endereço) | SecretBox |
| B | Log de auditoria sensível | SecretBox |
| C | Gravações de teleatendimento (v1+) | SecretBox |
| D | Backup client-side (par age — fora deste pacote) | age |
| E | TOTP secrets | SecretBox |
| F | HMAC de CPF para busca determinística | HMAC-SHA256 (NÃO cifra) |

A chave F é **HMAC**, não cifra. Guardas no código impedem uso errado.

## Problemas comuns

### "port is already allocated"
Só a porta 8000 do Django é exposta no host. Se outro app usar, mude em `docker-compose.yml`:
```yaml
ports:
  - "8001:8000"
```

### "Chave X não encontrada"
Rode `python3 scripts/generate_dev_keys.py` antes de qualquer coisa.

### "no such table: clinica_usuario"
Esqueceu o `migrate`. Rode `docker compose exec web python manage.py migrate`.

### "Argon2 is not supported"
Rebuild: `docker compose up --build --force-recreate web`.

## Status dos lotes

- [x] **Lote 1** — Infra Docker + Django base
- [x] **Lote 2 (v0.2.2)** — Models core + cifra multi-chave + API v1 + 39 testes na entrega original
- [ ] **Lote 3** — Registro clínico + autoria imutável + retificação + assinatura qualificada ICP-Brasil (integração futura)
- [ ] **Lote 4** — Agenda + faltas + feriados
- [ ] **Lote 5** — Documentos + upload seguro + ClamAV
- [ ] **Lote 6** — Portal responsável
- [ ] **Lote 7** — Log auditoria com hash encadeado + Loki
- [ ] **Lote 8** — Frontend React

## O que ainda não está implementado (apesar de estar na documentação)

Honestidade: a documentação do vault descreve controles planejados, muitos ainda não implementados em código. Lista:

- YubiKey / WebAuthn
- MFA real (TOTP ainda, planejado)
- Log append-only (trigger PG — Lote 7)
- Loki para espelhamento de log
- Wazuh HIDS
- Rate limiting
- Backup real (precisa VPS)
- Rotação de chaves (procedimento documentado, não ensaiado)
- Resposta a incidente (procedimento no cofre — não escrito ainda)
- Portal do responsável (Lote 6)
- ClamAV + pipeline seguro de upload (Lote 5)
- Assinatura qualificada ICP-Brasil (integração futura — Lote 3)

Estado atual de cada item: usar vocabulário objetivo —
`identificado → decidido → modelado → implementado → testado → validado externamente → em produção`.

## Documentação técnica completa

Modelo de ameaças e critérios de segurança antes do Lote 3:
[STRIDE](docs/seguranca/STRIDE-lote-3.md). Inclui riscos ainda pendentes;
documentação não equivale à implementação dos controles.

Permissões de escrita e limites da etapa atual:
[matriz cadastral](docs/seguranca/PERMISSOES-CADASTRAIS.md).

No vault Obsidian em `Memoria Claude/02-Pessoal/prontuario-espaco-desenvolver/`.

Registro, retificação e adendo: [documentação](docs/seguranca/REGISTRO.md).
Decisão e requisitos para a futura [assinatura ICP-Brasil](docs/integracoes/assinatura-icp-brasil.md).

Separação do perfil técnico: [TI e administração](docs/seguranca/PERFIL-TI.md).
