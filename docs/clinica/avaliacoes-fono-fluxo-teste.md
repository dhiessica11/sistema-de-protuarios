# Fluxo experimental de avaliações de fonoaudiologia

Disponível somente na configuração de desenvolvimento, com dados fictícios. A área
fica visível para uma conta fono vinculada ao paciente. Não há interpretação nem
pontuação automática de protocolos, integração com fonIA ou assinatura eletrônica.
A utilização assistencial depende de validação clínica, controles de produção e
requisitos jurídicos ainda pendentes.

A fonoaudióloga informa o protocolo, data, eventuais observações e zero ou mais
dificuldades (uma por linha). Cada dificuldade gera um rascunho textual que solicita
definição de um objetivo. Esse rascunho não é orientação clínica nem objetivo
aprovado. A profissional pode registrar uma decisão de aprovação ou de não inclusão
com seu próprio texto; decisões posteriores são adicionadas ao histórico. Ainda não
existe plano terapêutico formal, metas, priorização ou assinatura.

Uma reavaliação referencia uma avaliação anterior do mesmo paciente e protocolo,
com data igual ou posterior. O seletor apresenta as avaliações da página atual do
histórico; para selecionar uma avaliação antiga, navegue até a página correspondente.
A lista de pacientes e o acesso aos dados seguem o vínculo ativo. Apenas fono tem
acesso a essa API; administração, TI e outras categorias não recebem os conteúdos.

Textos são cifrados no banco. Na API, autores são definidos pelo servidor e não há
alteração ou exclusão das avaliações, dificuldades e decisões. Em PostgreSQL, uma
trigger bloqueia UPDATE e DELETE dessas tabelas; SQLite não aplica essa proteção,
e superusuários ou proprietários do banco podem desativar triggers. O controle de
origem no PostgreSQL verifica paciente e data; a conferência do protocolo é na API.
Não há importação de planilhas, classificação, cálculo de normas ou avaliação de
instrumentos validados. As bases de dados de desenvolvimento não são de produção.
