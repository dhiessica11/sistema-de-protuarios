# Registro: autoria e privacidade

**Exceção para desenvolvimento:** com `DEBUG`, `WEB_CONSULTA_HABILITADA` e
`ADMIN_CLINICO_DADOS_FICTICIOS` ativos, admin pode ler e criar registros de teste
de todas as categorias, com autoria atribuída à conta admin. Em novos registros
fictícios, a categoria simulada é indicada explicitamente; não representa
qualificação profissional. A exceção não autoriza uso com dados reais.

O Registro armazena paciente, autor, categoria histórica, resumo e detalhe cifrados
com a chave A, indicador de compartilhamento e data de criação. O servidor define
autor e categoria a partir do profissional autenticado; esses campos não são aceitos
no payload. A criação exige vínculo ativo com o paciente.

Na API, profissionais com vínculo ativo leem o detalhe de registros da própria
categoria. Outra categoria acessa somente o resumo quando o registro é marcado como
compartilhado. Registros não compartilhados não aparecem na lista nem no detalhe
de outra categoria. Administração, TI e profissionais sem vínculo não recebem o
conteúdo clínico por esse endpoint. PUT, PATCH e DELETE não estão habilitados.

Em PostgreSQL, a trigger `registro_autoria_imutavel` rejeita alterações de autor,
categoria e paciente, inclusive em operações SQL diretas. A trigger adicional
`registro_preservar` rejeita UPDATE e DELETE de registros existentes, preservando
o conteúdo original para retificações e adendos. A migration do modelo
foi gerada pelo Django; a migration vazia da trigger também foi gerada pelo Django
e recebeu a operação SQL específica, com reversão. A proteção não impede alterações
por administrador de banco capaz de desabilitar a trigger; a role de aplicação deve
ser separada da role proprietária das migrations. SQLite não executa essa trigger.

## Retificação e adendo

Retificações e adendos são registros novos, com `origem` apontando para o registro
anterior e autor definido pelo servidor. A retificação exige justificativa com pelo
menos 50 caracteres e identificação de quem foi contatado para validação; ambos os
campos são cifrados. Adendo pode ser criado sem justificativa ou contato. O contato
informado é uma declaração do profissional, não prova independente da consulta. Uma retificação pode
apontar para outra, formando uma árvore. O original permanece inalterado.

Por padrão de privacidade, o autor do novo registro precisa ter vínculo ativo com o
paciente e pertencer à mesma categoria histórica da origem; essa proteção também é
aplicada ao adendo. A origem precisa pertencer ao mesmo paciente. Para outra categoria,
o resumo compartilhado não revela o detalhe, a justificativa ou o identificador da
origem privada. O cliente não pode indicar autor, categoria ou assinatura.

A API calcula `estado_assinatura: sem_assinatura` para todos os registros, inclusive
resumos compartilhados. O campo não é evidência nem implementação de assinatura.
Não existe assinatura eletrônica
implementada nem evidência de assinatura: os novos registros não devem ser tratados
como retificações clínicas finalizadas. A decisão e os requisitos da futura
assinatura estão em `docs/integracoes/assinatura-icp-brasil.md`.

A proteção do PostgreSQL não impede TRUNCATE nem um owner/superuser de desabilitar
triggers. A role de aplicação deve ter privilégios limitados. SQLite não implementa
essas triggers. O mínimo de 50 caracteres é validado pela API; o banco verifica
apenas a presença de justificativa e contato, pois os campos estão cifrados.
MFA efetivo e auditoria append-only continuam pendentes. Não usar
com dados reais até implementar e validar os controles do projeto.
