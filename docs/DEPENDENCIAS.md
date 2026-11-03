# Dependências do backend

As faixas compatíveis ficam em `backend/pyproject.toml`. As versões exatas,
inclusive transitivas e ferramentas, ficam em `backend/requirements-dev.lock`,
gerado por pip-tools com hashes. Docker de desenvolvimento e CI usam esse arquivo.
O lock foi gerado e validado com Python 3.12 em Linux; outras versões/plataformas
precisam de validação própria antes de serem consideradas suportadas.

## Instalar no ambiente virtual

Dentro de `backend/`, com o ambiente virtual ativado:

```bash
python -m pip install --require-hashes -r requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
python -m pip check
```

O código local é instalado separadamente, sem resolver novas dependências.
Pip, setuptools e wheel também estão fixados no lock. O Docker continua sendo
de desenvolvimento, com as ferramentas de teste já presentes na versão anterior.

## Atualizar

Editar as faixas necessárias no pyproject e executar com Python 3.12:

```bash
pip-compile --extra dev --generate-hashes --allow-unsafe --strip-extras \
  --no-emit-index-url --no-emit-trusted-host \
  --output-file requirements-dev.lock pyproject.toml
```

Usar `--upgrade-package nome` para atualizar uma dependência já travada; `--upgrade`
atualiza todas as dependências dentro das faixas permitidas. Revisar o diff do lock.
Em um ambiente virtual novo, instalar e executar:

```bash
pip-audit --strict --require-hashes --disable-pip -r requirements-dev.lock
ruff check .
ruff format --check .
bandit -r apps config -ll
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py makemigrations --check --dry-run
DJANGO_SETTINGS_MODULE=config.settings.test python manage.py migrate --noinput
pytest --cov=apps --cov=config --cov-report=term-missing --cov-fail-under=70
```

Repetir migrations e testes com PostgreSQL 16 via `DATABASE_URL`. A auditoria
consulta o catálogo de vulnerabilidades e falha também se não conseguir completar
a consulta. Nenhum erro é ignorado no CI. Resultado limpo é uma verificação das
vulnerabilidades conhecidas naquele momento, não uma garantia geral de segurança.

## Compatibilidade Django 5.2

O backend migrou de Django 5.1 para 5.2 LTS para receber as correções disponíveis.
O antigo `STATICFILES_STORAGE` foi substituído por `STORAGES`, mantendo WhiteNoise
para arquivos estáticos e FileSystemStorage como backend padrão de arquivos.
