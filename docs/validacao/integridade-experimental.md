# Validação da impressão digital experimental

Data: 2026-11-03. Código testado com PostgreSQL 16 em ambiente isolado e dados
sintéticos. Não houve chamada ao gov.br nem uso de credenciais de homologação.

- Suíte completa: 242 testes passaram; cobertura de 89,09%.
- Testes específicos: 18 passaram após a formatação final.
- Ruff, verificação de migrations, migrate e Bandit no nível do CI passaram.
- Os testes verificam repetibilidade, leitura do estado persistido, diferenças
  em cada campo, falha diante de mudança do esquema e cifra do texto no banco.

Essa verificação não comprova assinatura, identidade do signatário, representação
documental adequada ou viabilidade da API para a clínica. Veja
`docs/integracoes/integridade-experimental.md` para as limitações e não utilize
a função como evidência de assinatura.
