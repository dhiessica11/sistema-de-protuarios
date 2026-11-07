# Validação de Registro: autoria e privacidade

> Nota atual: referências à obrigatoriedade gov.br abaixo são históricas; a decisão vigente é a [integração futura ICP-Brasil](../integracoes/assinatura-icp-brasil.md).

**Atualização posterior:** a migration `0005` também passou a rejeitar UPDATE e
DELETE do conteúdo no PostgreSQL. A observação contrária abaixo descreve a revisão
anterior; consulte `retificacao-adendo.md` para o estado e os limites atuais.

Data: 2026-11-03. Base: main após PR #3. Backend montado na imagem de desenvolvimento
v0.2.4, com PostgreSQL 16 isolado. Foram usados apenas dados sintéticos.

- Migration `0003_registro` gerada pelo Django e aplicada.
- Migration vazia `0004_proteger_autoria` gerada pelo Django e preenchida com
  operação SQL reversível para a trigger PostgreSQL. Reversão e reaplicação: OK.
- Autor, categoria e paciente não podem ser alterados por UPDATE enquanto a
  trigger estiver habilitada. Testes usam ORM e SQL direto em PostgreSQL.
- API define autor/categoria no servidor e rejeita campos de autoria no payload.
- Lista e detalhe respeitam equipe ativa, conta ativa e categoria. As seis
  combinações entre categorias verificam que apenas resumo compartilhado sai
  para outra categoria; detalhe privado não é retornado.
- Sem vínculo ativo, conta inativa, usuário anônimo e administração são bloqueados.
- O detalhe é armazenado cifrado; PUT, PATCH e DELETE não são expostos na API.
- Suíte completa: **191 testes passaram**, cobertura **87,08%**. Ruff e verificação
  de migrations sem drift passaram; migrations aplicadas no PostgreSQL.

A trigger se aplica ao PostgreSQL, não ao SQLite. Sua proteção depende de a role de
execução não ter poderes de desabilitá-la. Edição de conteúdo e exclusão por SQL
direto não são bloqueadas por esta trigger. A assinatura gov.br, retificação, adendo,
MFA efetivo e auditoria completa permanecem pendentes; esta validação não autoriza
uso com dados reais. Detalhes do contrato em `docs/seguranca/REGISTRO.md`.
