# Decisão: assinatura qualificada ICP-Brasil

**Estado:** decidida como objetivo do projeto; integração, fornecedor e mecanismo
de uso ainda não definidos nem implementados. Esta decisão substitui a exigência
anterior de integração com a API de assinatura gov.br. A pesquisa anterior está
preservada em [govbr-viabilidade.md](govbr-viabilidade.md).

O projeto pretende usar assinatura eletrônica qualificada com certificado
ICP-Brasil individual do profissional autor. A existência, validade e modalidade
dos certificados dos profissionais ainda devem ser confirmadas; não se presume
que a clínica ou toda a equipe já os possua. A1, A3 ou certificado em nuvem são
possibilidades a avaliar conforme o certificado, a infraestrutura e o fluxo real.
Não há fornecedor escolhido nem credenciais configuradas por esta decisão.

## Estado atual

Não existe assinatura eletrônica implementada. A API informa `sem_assinatura`;
nenhum registro deve ser apresentado como assinado ou clinicamente finalizado
com base no estado atual. A [impressão digital experimental](integridade-experimental.md)
é apenas um hash interno, não uma assinatura nem prova de aprovação ou identidade.
O Lote 3 permanece aberto. Os demais controles de segurança e produção continuam
pendentes; não utilizar dados reais nesta etapa.

## Requisitos para a integração futura

- Confirmar o certificado individual, sua validade, modalidade, compatibilidade
  com os computadores dos profissionais e como cada assinatura será autorizada.
  Não compartilhar certificados, chaves privadas ou senhas entre profissionais.
- Escolher formato e mecanismo de assinatura e validação antes da implementação;
  avaliar fornecedores, custos, condições contratuais, tratamento de dados de saúde
  e compatibilidade com o ambiente autogerido. Nenhum fluxo manual foi implementado.
- Vincular a identidade verificada do titular do certificado ao autor do registro,
  preservar identificação profissional e registro no conselho da época e assegurar
  a manifestação de vontade do profissional sobre o conteúdo exato.
- Preservar o artefato ou bytes exatos assinados, a assinatura e evidências necessárias
  à verificação posterior, incluindo cadeia do certificado e situação de validade e
  revogação conforme o mecanismo adotado. Avaliar carimbo do tempo quando aplicável.
- Preservar o registro original e sua evidência; retificações e adendos devem ser
  novos registros vinculados, assinados pelo respectivo autor, sem alterar o original.
- Testar divergência entre autor e certificado, alterações no conteúdo, certificados
  inválidos ou revogados, falhas e repetição de requisições. Falha ou ausência de
  evidência verificada não pode resultar em estado assinado.
- Validar os requisitos jurídicos e profissionais aplicáveis a cada categoria e tipo
  de documento, incluindo CFP e COFFITO, além dos requisitos de sigilo e guarda.

Fontes: [ITI — certificação digital](https://www.gov.br/iti/pt-br/acesso-a-informacao/perguntas-frequentes/certificacao-digital),
[Lei 14.063/2020](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2020/lei/l14063.htm)
e [Resolução CFFa 777/2025](https://www.fonoaudiologia.org.br/resolucoes/resolucoes_html/CFFa_N_777_25.htm).
