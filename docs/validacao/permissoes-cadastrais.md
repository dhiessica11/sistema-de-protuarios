# Validação — permissões cadastrais

Data: 2026-11-03. Base: main `e7d23bec79b484a445bde4c769a939beb8db2126`, após merge
do STRIDE/PR #2. Escopo: API de Paciente e Responsavel e justificativa de identificação.

## Alterações

- Matriz por campo aplicada antes da validação de valores para PUT/PATCH.
- Profissionais das três categorias restritos a nome social, status e encerramento
  dos próprios pacientes; sem edição de responsáveis ou campos administrativos.
- Administração sem alteração de status/encerramento clínico.
- Justificativa obrigatória de identificação persistida com chave B na mesma transação.
- Novo model AlteracaoCadastral e `0002_alteracaocadastral.py`, gerada por makemigrations.
- Aliases de nome/CPF corrigidos; CPF normalizado e hash limpo ao remover CPF opcional.
- Atualização relê e trava o cadastro antes de validar e salvar, preservando alterações
  de outro perfil e a exigência de motivo quando o snapshot ficou antigo.
- Atualização de responsável registra o usuário responsável pela edição em atualizado_por.

## Verificações executadas

Código montado sobre a imagem de desenvolvimento validada da v0.2.4, com o mesmo
lockfile de dependências. Testes com configurações de teste; PostgreSQL 16 executado
em Compose isolado para esta tarefa. Nenhum dado real foi utilizado.

- **180 testes passaram** tanto em SQLite quanto em PostgreSQL 16.
- Cobertura: **86,42%**, acima do mínimo de 70%.
- Ruff lint limpo; 40 arquivos formatados.
- Migration gerada pelo Django, aplicada e sem drift; system check sem problemas.
- Bandit no nível do CI: zero achados médios/altos; 137 baixos, incluindo asserts dos testes.
- Sem alteração de dependências. A auditoria bloqueante permanece no CI.

Casos novos incluem PUT/PATCH por três categorias, payload misto sem persistência
parcial, vínculo ausente/inativo, permissões de leitura preservadas, edição legítima,
CPF/alias, injeção de campos internos, motivo vazio/curto/ausente, justificativa cifrada
no banco, rollback da mudança se a evidência falhar e snapshots desatualizados.
Os testes de snapshot simulam alterações intercaladas de forma determinística;
não são testes de carga ou de múltiplas conexões simultâneas.

## Limites

As restrições são da API, não de SQL direto. Justificativa persistida não substitui
auditoria completa, nem prova conferência real de documento. Separação TI/admin,
troca de guarda completa, portal, assinatura e privacidade do texto clínico por
categoria continuam pendentes. Não foram repetidos o build e a validação completa
de web/worker/Redis: não houve mudança de dependências ou Compose.

Evidências: `permissoes-postgres.txt` e `permissoes-sqlite.txt`. O resultado do
GitHub Actions da nova PR é verificável separadamente no repositório.
