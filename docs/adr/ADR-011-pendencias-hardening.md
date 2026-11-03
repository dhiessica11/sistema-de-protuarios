# ADR-011 — Pendencias de hardening reconhecidas

**Data:** 2026-11-02
**Status:** Aceita (lista de debito tecnico ciente)

## Contexto

**Atualização em 2026-11-03:** os itens abaixo preservam o registro original de
2026-11-02. Lockfile, auditoria bloqueante e PostgreSQL/Compose foram implementados
e testados nas v0.2.3/v0.2.4; seus relatos históricos de pendência não representam
o estado atual. A análise STRIDE está documentada em
`docs/seguranca/STRIDE-lote-3.md`, com riscos, evidências e critérios de saída.
As permissões por campo de Paciente/Responsavel e justificativas de identificação
estão implementadas/testadas na revisão descrita em
`docs/seguranca/PERMISSOES-CADASTRAIS.md`. Privacidade de texto clínico por categoria
depende de Registro. Separação TI/admin e os demais controles continuam pendentes.
Dependabot ainda não foi configurado; não confundir com o pip-audit bloqueante.

Review externa levantou pontos legitimos que nao sao resolvidos em v0.2.2
mas precisam ser rastreados para nao se perderem.

## Debitos tecnicos aceitos

### 1. TI nao e admin — e papel operacional separado
Hoje `tipo="ti"` e tratado como admin (`eh_admin = True`). Isso significa que
a Dhiessica (que opera o sistema) ve todos os dados clinicos no dia a dia.

**Decisao futura (Lote 7):**
- Separar `is_admin` de `is_ti`
- TI acessa dashboards tecnicos, logs, infra — NAO dados clinicos sem
  procedimento emergencial
- Acesso TI a dados clinicos exige "modo emergencial" com log reforcado
  e aprovacao da Rosanita

### 2. Permissoes por campo
Hoje profissional vinculado edita qualquer campo do paciente.

**Decisao futura (Lote 3 ou 4):**
- Campos administrativos (contato, endereco) — admin
- Campos de identificacao (nome civil, CPF) — admin com justificativa
- Campos clinicos (status, encerramento) — profissional vinculado
- Nome social — profissional ou responsavel

### 3. Lockfile de dependencias
`==5.1.*` ainda permite patch autoupdate. Reinstalacao pode mudar comportamento.

**Decisao futura (Lote 3):**
- Gerar `requirements.lock` com `pip-compile` do pip-tools
- CI usa `pip-sync requirements.lock` em vez de `pip install -e`
- Renovacao de lock controlada (PR dedicado por versao)

### 4. pip-audit bloqueando CI
Hoje: `pip-audit --strict || true` — informativo apenas.

**Decisao futura (Lote 3):**
- `pip-audit --strict` sem `|| true` — bloqueia build se CVE
- Alem disso: Dependabot ativo no repo

### 5. Validacao em PostgreSQL 16
v0.2.2 validada em SQLite in-memory (CI usa Postgres, dev local tambem).

**Decisao futura (antes de Lote 3):**
- CI roda testes em Postgres 16 (ja esta configurado em `.github/workflows/ci.yml`)
- Documentar passo "pytest no Docker" como validacao oficial

### 6. Rotacao da chave F exige recomputar hashes de CPF
Mudar chave F significa que todos os `cpf_hash` ficam invalidos.

**Decisao futura:**
- Comando `python manage.py rotate_key_f --old-key=X --new-key=Y` que:
  1. Para o sistema (manutencao)
  2. Recomputa `cpf_hash` com nova chave em todas as tabelas afetadas
  3. Verifica unicidade (nao pode colidir)
  4. Troca o Docker secret
  5. Religa o sistema
- Procedimento vai no runbook em papel

### 7. Validacao do bloqueio de criacao antes do serializer
Teste `test_fono_nao_pode_criar_paciente` agora manda payload vazio.
Melhor: mandar payload valido e verificar que ainda retorna 403.

**Decisao futura:**
- Adicionar `test_fono_nao_pode_criar_paciente_mesmo_com_payload_valido`
  no Lote 3 quando ja houver infra pra criar paciente valido no teste

### 8. Validacao de localizacao do comprovante
`comprovante_vinculo_pendente` e TextField livre. Risco de registrar PII.

**Decisao futura (Lote 5):**
- Quando implementar upload real, migrar texto livre para FileField com
  pipeline seguro
- Enquanto isso, documentar na UI que nao deve conter dados pessoais

## Nao-decisoes (aceito e segue)

- Falta de ensaio real da cerimonia de chave — pre go-live
- Threat model STRIDE formal — pre Lote 3
- Consultoria juridica (matriz CFP/COFFITO) — contratar quando o resto estiver pronto
- RIPD formal — contratar consultor LGPD
- Lockfile — Lote 3
