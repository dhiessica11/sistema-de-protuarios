# Fluxo experimental de avaliações de fonoaudiologia

Disponível somente na configuração de desenvolvimento, com dados fictícios. A área
fica visível para uma conta fono vinculada ao paciente e para a conta admin no modo
de dados fictícios. Não há interpretação nem
pontuação automática de protocolos, integração com fonIA ou assinatura eletrônica.
A utilização assistencial depende de validação clínica, controles de produção e
requisitos jurídicos ainda pendentes.

A fonoaudióloga informa o protocolo, data, eventuais observações e zero ou mais
dificuldades (uma por linha). Cada dificuldade gera um rascunho textual que solicita
definição de um objetivo. Esse rascunho não é orientação clínica nem objetivo
aprovado. A profissional pode registrar uma decisão de aprovação ou de não inclusão
com seu próprio texto; decisões posteriores são adicionadas ao histórico. Planos de teste permitem selecionar revisões aprovadas, informar metas e período,
recursos e orientações. Não há priorização, plano clinicamente finalizado nem assinatura.

Uma reavaliação referencia uma avaliação anterior do mesmo paciente e protocolo,
com data igual ou posterior. O seletor apresenta as avaliações da página atual do
histórico; para selecionar uma avaliação antiga, navegue até a página correspondente.
Fonoaudiólogas seguem o vínculo ativo. A conta admin pode consultar e operar dados
fictícios sem vínculo, com autoria registrada como admin; TI e outras categorias
não recebem esses conteúdos. Essa exceção exige simultaneamente DEBUG,
WEB_CONSULTA_HABILITADA e ADMIN_CLINICO_DADOS_FICTICIOS, habilitados em dev; não
é uma regra de produção.

Textos são cifrados no banco. Na API, autores são definidos pelo servidor e não há
alteração ou exclusão das avaliações, dificuldades e decisões. Em PostgreSQL, uma
trigger bloqueia UPDATE e DELETE dessas tabelas; SQLite não aplica essa proteção,
e superusuários ou proprietários do banco podem desativar triggers. O controle de
origem no PostgreSQL verifica paciente e data; a conferência do protocolo é na API.
Planos e itens são preservados no PostgreSQL; cada item mantém a revisão que o
fundamentou. Novos planos exigem a última revisão aprovada de cada dificuldade. O
seletor apresenta objetivos aprovados da página atual de avaliações. Novas revisões
não alteram planos anteriores.
Correções de avaliações, planos e sessões criam uma nova versão, sem sobrescrever
a anterior. Ao corrigir uma avaliação, as novas dificuldades exigem revisão; as
revisões de avaliações antigas não podem ser usadas em novos planos. Sessões
corrigidas deixam de ser contabilizadas na evolução, evitando duplicação. A
visualização e uso de versões antigas continuam disponíveis no histórico.

Não há importação de planilhas, classificação, cálculo de normas ou avaliação de
instrumentos validados. As bases de dados de desenvolvimento não são de produção.
