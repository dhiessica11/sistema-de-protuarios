# ADR-010 — Correcoes de codigo apos review externa (v0.2.2)

**Data:** 2026-11-02
**Status:** Aceita e VALIDADA executando pytest + ruff + makemigrations check

## Contexto

Duas rounds de review externa (IAs independentes) identificaram bugs criticos
na primeira v0.2.1. v0.2.2 corrige todos.

## Problemas da v0.2.1 corrigidos

### 1. `pip install -e` falhava
Setuptools nao sabia encontrar os pacotes `apps` e `config`.

**Fix:** Adicionado `[build-system]` + `[tool.setuptools]` com `packages`
e `py-modules` explicitos.

### 2. Migration manual divergente dos models
`0001_initial.py` escrita a mao tinha drifts (manager, constraints,
indices, etc).

**Fix:** Migration regenerada por `python manage.py makemigrations`, agora
real e sem drift. CI valida com `--check --dry-run`.

### 3. 4 testes falhavam
- `test_fono_nao_pode_criar_paciente` esperava 403, retornava 400 (payload invalido
  antes da checagem de permissao)
- `test_admin_nao_pode_deletar_paciente` esperava 405, retornava 403 (SemDelete
  cortava antes de http_method_names)
- Mesmo problema em `test_admin_nao_pode_deletar_responsavel`
- `test_health_endpoint_returns_200` sem `@pytest.mark.django_db`

**Fix:**
- `get_permissions` por action (`create` exige `IsAdmin` ANTES do serializer)
- Removido `SemDelete`; `http_method_names` sozinho entrega 405 correto
- `test_health` agora com decorador correto

### 4. Falta de validacao de escopo em consentimento
Fono podia criar consentimento para paciente fora da sua equipe
informando apenas o UUID.

**Fix:** `ConsentimentoSerializer.validate()` agora checa:
- Responsavel realmente pertence ao paciente informado
- Profissional nao-admin so cria para pacientes do seu escopo

2 novos testes cobrem (`TestConsentimentoEscopo`).

### 5. Lint falhando (10 ruff errors + 20 arquivos a reformatar)

**Fix:** `ruff check --fix .` + `ruff format .` aplicados.
CI continua rodando ambos.

### 6. Imprecisoes na documentacao
- "16 testes novos" (era 14 + 1 health)
- "38 testes" (era 37)
- README dizia `makemigrations` (migration ja versionada)
- README listava 8 ADRs (sao 10)

**Fix:** README e INSTALAR atualizados com numeros reais (22 + 16 + 1 = 39).

## Correcoes de permissao (ja aceitas da primeira rodada)

- `PacienteEquipeViewSet` tem queryset filtrado agora
- `PacienteNoScopeDoProfissional` para object-level
- `IsAdmin` para `create` em pacientes, responsaveis, vinculo-equipe
- DELETE bloqueado via `http_method_names` em todos clinicos
- Consentimento sem PUT/PATCH

## Correcoes de dados sensiveis (ja aceitas)

- `hash_cpf` migrado para HMAC-SHA256 com chave F dedicada
- Chave F guardada separadamente, impedida de ser usada para cifrar
- `comprovante_vinculo` (FileField) desabilitado → `comprovante_vinculo_pendente`
  (TextField com descricao de onde foi arquivado offline). Pipeline seguro
  no Lote 5.
- Postgres e Redis nao expostos no host por padrao

## Verificacao executada

```bash
# Todas as checagens do CI passam localmente (Python 3.13.16, SQLite):

[1/5] pip install -e ".[dev]"       -> Successfully installed prontuario-ed-0.2.2
[2/5] makemigrations --check         -> No changes detected
[3/5] ruff check .                   -> All checks passed!
[4/5] ruff format --check .          -> 35 files already formatted
[5/5] pytest -v                      -> 39 passed in 0.72s
```

## O que v0.2.2 explicitamente NAO fecha

Fica para ADRs futuros / lotes posteriores:

- **Assinatura avancada CFFa Art. 6** (gov.br obrigatorio no MVP) — Lote 3
- **Matriz legal CFP + COFFITO + CFFa + LGPD** — requer consultoria juridica externa
- **RIPD formal** — requer consultor LGPD (R$ 3.500-6.000)
- **Threat model STRIDE formal** — antes do Lote 3
- **Validacao operacional da cerimonia de chave** — ensaio real pre-go-live
- **Lockfile real** (pip-compile) — release 0.3.0 (Lote 3)
- **Validacao em PostgreSQL 16** (atual roda em SQLite in-memory) — testar com
  `docker compose` real pre-go-live
- **Rotacao real das chaves** (procedimento documentado nao ensaiado)
- **Separacao do tipo TI** do admin (atualmente TI tem mesmos poderes)
- **Separacao de permissoes por campo** (atualmente profissional vinculado pode
  editar qualquer campo do paciente)
- **Pin exato de versoes** (`==5.1.*` ainda permite patch)
- **`pip-audit --strict` bloqueando CI** (atualmente so informativo)

Esses pontos estao reconhecidos. Nao bloqueiam Lote 3 mas serao enderecados.
