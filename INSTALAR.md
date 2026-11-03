# Instalação — desenvolvimento após v0.2.4

**Esta revisão foi validada:** 180/180 testes passam, lint limpo, migration sem drift, pip install funciona.
Substitui qualquer download anterior.

## Pré-requisito

**Atualização de dependências:** Docker e CI agora usam o lockfile com hashes.
Reconstrua as imagens com `docker compose build --no-cache` ao substituir esta
versão. Veja `docs/DEPENDENCIAS.md` para instalação sem Docker e atualização do lock.

Docker Desktop (ícone de baleia visível). Download: https://www.docker.com/products/docker-desktop

## Passo 1 — Extrair

- **Mac:** duplo clique no `.tar.gz`
- **Windows:** 7-Zip → "Extrair aqui"
- **Linux:** `tar -xzf prontuario-ed-v0.2.2.tar.gz`

Entra na pasta `prontuario-ed`.

## Passo 2 — Terminal na pasta

**Mac:** clica direito → "Novo Terminal na pasta"
**Windows:** no Explorador, barra de endereço → digita `powershell` → Enter
**Linux:** `cd ~/caminho/para/prontuario-ed`

Confirma:
```bash
ls
# Deve mostrar: backend/ docs/ infra/ scripts/ docker-compose.yml README.md ...
```

## Passo 3 — Gerar 5 chaves de cifra DEV (A, B, C, E, F)

```bash
python3 scripts/generate_dev_keys.py
```

Deve criar 5 arquivos em `secrets_dev/`:
```
[ok] secrets_dev/key_a.bin (32 bytes)
[ok] secrets_dev/key_b.bin (32 bytes)
[ok] secrets_dev/key_c.bin (32 bytes)
[ok] secrets_dev/key_e.bin (32 bytes)
[ok] secrets_dev/key_f.bin (32 bytes)   # usada para HMAC de CPF
```

Chave D (backup) é separada — fica para o pipeline de deploy.

## Passo 4 — Configurar .env

```bash
# Mac/Linux
cp .env.example .env

# Windows PowerShell
Copy-Item .env.example .env
```

Gerar DJANGO_SECRET_KEY e colar no `.env`:
```bash
python3 -c "import secrets; print('DJANGO_SECRET_KEY=' + secrets.token_urlsafe(50))"
```

## Passo 5 — Subir (primeira vez 5-10min)

```bash
docker compose up --build
```

Baixa imagens, instala deps.

Quando parar de rolar e mostrar:
```
prontuario-web | Starting development server at http://0.0.0.0:8000/
```

Deixa esse terminal aberto.

## Passo 6 — Em outro terminal, aplicar migrations

```bash
cd ~/caminho/para/prontuario-ed

# NAO precisa makemigrations - migration JA esta versionada no repo
docker compose exec web python manage.py migrate
```

Deve aparecer "OK" em cada migration aplicada.

## Passo 7 — Criar superuser

```bash
docker compose exec web python manage.py createsuperuser
```

- Username: `dhiessica` (ou outro)
- Email: opcional (pode deixar vazio)
- Password: mínimo 12 caracteres

## Passo 8 — Validar

**Revisão de permissões:** aplique também a migration `0002_alteracaocadastral` incluída nesta revisão; ela armazena as justificativas de identificação cifradas.

### Health
```bash
curl http://localhost:8000/health/
# {"status": "ok", "service": "prontuario-ed"}
```

### Admin
`http://localhost:8000/admin/` — deve mostrar APENAS:
- Grupos (padrão Django)
- Usuarios
- Clinicas

**NÃO deve mostrar** Pacientes/Responsáveis/Consentimentos/Vínculos (proposital — ADR-005).

### API
`http://localhost:8000/api/v1/` — lista 6 endpoints.

### Testes — 180 passando
```bash
docker compose exec web pytest -v
```

Esperado:
```
test_health.py::test_health_endpoint_returns_200 PASSED
... (22 testes de invariantes)
... (16 testes de autorização)
======= 180 passed in X.XXs =======
```

### Lint
```bash
docker compose exec web ruff check .
# All checks passed!

docker compose exec web ruff format --check .
# 40 files already formatted
```

### Migration drift
```bash
docker compose exec web python manage.py makemigrations --check --dry-run
# No changes detected
```

## Como parar

Terminal 1 (onde está preso):
```
Ctrl + C
```

```bash
docker compose down
# ou (apaga dados):
docker compose down -v
```

## Problemas comuns

| Erro | Causa | Solução |
|---|---|---|
| `Cannot connect to Docker daemon` | Docker Desktop fechado | Abre o Docker |
| `port 8000 already in use` | Outro Django | Mude para `8001:8000` em `docker-compose.yml` |
| `Chave F nao encontrada` | Esqueceu passo 3 | `python3 scripts/generate_dev_keys.py` |
| `no such table` | Esqueceu passo 6 | `migrate` |
| `Argon2 is not supported` | Build antigo | `docker compose up --build --force-recreate web` |

## Próximo passo

Validou tudo? Me diz **"v0.2.2 ok"** → eu começo:
1. Atualização completa do vault (Dec 1 + Dec 2 incorporadas + inconsistências DPO corrigidas)
2. Lote 3 com assinatura gov.br obrigatória no modelo

## O que v0.2.2 corrigiu da v0.2.1

| Problema v0.2.1 | Fix v0.2.2 |
|---|---|
| `pip install -e` falhava (setuptools sem config) | `[tool.setuptools]` com packages explícitos |
| Migration manual divergente | Regenerada pelo Django, versionada |
| 4 testes falhavam | 39/39 passando na v0.2.2 |
| Lint reportava 10 erros + 20 arquivos | 0 erros, 0 arquivos pra reformatar |
| Permissão de criação avaliada tarde (400 vs 403) | `get_permissions` por action — 403 agora |
| DELETE retornava 403 em vez de 405 | Removido `SemDelete`, só `http_method_names` |
| Consentimento sem validação de escopo | Serializer valida escopo + paciente/responsável |
| test_health sem `@pytest.mark.django_db` | Fixed |
| README dizia 16 testes (era 14 + health quebrado) | Agora diz 39, batem com realidade |
| INSTALAR dizia `makemigrations` | Removido — migration já versionada |
