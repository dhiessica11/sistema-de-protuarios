# Validação: preservação, retificação e adendo

Data: 2026-11-03. Base: main após PR #4. Testes com dados sintéticos e PostgreSQL 16.

## Implementação

- Trigger `registro_preservar`: rejeita UPDATE e DELETE de registro existente.
- Retificação e adendo criam novo registro com origem; o original não é modificado.
- Origem do mesmo paciente e categoria é exigida na API e por trigger PostgreSQL;
  o profissional deve estar ativo e vinculado ao paciente. A mesma regra de categoria
  também foi aplicada ao adendo para preservar a privacidade da origem.
- Retificação exige justificativa de pelo menos 50 caracteres e identificação de
  quem foi consultado. Adendo não exige esses campos. O contato é autodeclarado.
- Justificativa e contato são cifrados. Na leitura por outra categoria, a consulta
  não carrega esses campos nem o detalhe; apenas resumo compartilhado é retornado.
- Retificação de retificação é permitida. O novo registro tem autoria do profissional
  que o criou. A API informa `sem_assinatura` e rejeita um estado enviado pelo cliente.

## Evidências

- Suíte completa: **206 testes passaram** em PostgreSQL; cobertura **87,55%**.
- Suíte específica posterior: **31 testes passaram**, incluindo outro profissional
  da mesma categoria, origens compartilhadas, justificativa/contato cifrados,
  ausência de contato e consulta sem campos privados.
- Em SQLite, a suíte específica anterior passou com 24 testes e três testes de
  trigger PostgreSQL ignorados; SQLite não oferece as mesmas garantias de banco.
- Ruff limpo; 49 arquivos formatados; migrations sem drift; Django system check OK.
- Bandit no nível do CI: nenhum achado médio/alto.
- Testada atualização de banco isolado contendo um registro anterior: migrations
  `0005` a `0008` aplicadas e conteúdo legado preservado. A reversão e reaplicação
  dessas migrations também foram executadas nesse banco sem dados reais.
- Django gerou as migrations de modelo e os esqueletos vazios. As operações SQL de
  trigger foram acrescentadas aos esqueletos e testadas em PostgreSQL.

O CI da PR executa a suíte na versão final. As triggers não se aplicam ao SQLite e
não impedem TRUNCATE nem alterações por owner/superuser capaz de desabilitá-las.
O banco verifica a presença da justificativa e do contato, enquanto o mínimo de 50
caracteres é validado na API porque o texto é cifrado. Roles restritas, MFA e auditoria
completa permanecem pendentes.

Não há assinatura eletrônica implementada. As retificações e os adendos não são
clinicamente finalizados por este código. A elegibilidade de acesso da clínica
privada à API gov.br está pendente de confirmação, conforme pesquisa em
`docs/integracoes/govbr-viabilidade.md`. Não utilizar dados reais nesta etapa.
