# Registro: autoria e privacidade

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
categoria e paciente, inclusive em operações SQL diretas. A migration do modelo
foi gerada pelo Django; a migration vazia da trigger também foi gerada pelo Django
e recebeu a operação SQL específica, com reversão. A proteção não impede alterações
por administrador de banco capaz de desabilitar a trigger; a role de aplicação deve
ser separada da role proprietária das migrations. SQLite não executa essa trigger.

Este é o recorte de autoria e privacidade solicitado. A trigger não impede edição
do conteúdo ou exclusão por SQL direto. Retificação, adendo, assinatura eletrônica
gov.br, MFA efetivo e auditoria append-only ainda não estão implementados. Não usar
com dados reais até implementar e validar os controles do projeto.
