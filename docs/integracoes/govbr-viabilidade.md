# Assinatura gov.br: viabilidade da integração

Pesquisa histórica: 2026-11-03. A obrigatoriedade de integração gov.br foi
substituída pela decisão de adotar assinatura qualificada ICP-Brasil; veja
[decisão atual](assinatura-icp-brasil.md). Este documento preserva a pesquisa
anterior. A elegibilidade da clínica privada não foi confirmada.

Atualização em 2026-11-07: o [Serviço de Integração aos Produtos de Identidade
Digital gov.br](https://www.gov.br/governodigital/pt-br/estrategias-e-governanca-digital/transformacao-digital/servico-de-integracao-aos-produtos-de-identidade-digital-gov.br)
informa que o acesso à integração é concedido apenas a sistemas de serviço público,
após análise individual, e que a solicitação deve ser formalizada por agente público.
Isso torna a integração direta de um prontuário de clínica privada um risco concreto
de inviabilidade. Não foi confirmada uma exceção ou via indireta aplicável ao caso;
não presumir que ela exista. A possibilidade jurídica e operacional da solução escolhida ainda precisa ser
confirmada para cada profissão e tipo de documento.

O [art. 6º da Resolução CFFa nº 777/2025](https://www.fonoaudiologia.org.br/resolucoes/resolucoes_html/CFFa_N_777_25.htm)
aceita assinatura eletrônica avançada **ou** qualificada para documentos ou
prontuários eletrônicos subscritos por fonoaudiólogos; o texto não exige gov.br
nominalmente. A escolha anterior por gov.br foi substituída pela decisão de
adotar ICP-Brasil. A análise jurídica, inclusive para CFP e COFFITO, segue pendente.

A responsável informou que a clínica ainda não possui acesso aprovado ao ambiente
de homologação. Não há credenciais configuradas no ambiente desta tarefa.
Existe uma [impressão digital interna experimental](integridade-experimental.md),
que não é integração nem assinatura e não deve ser usada como evidência.

A página oficial [Assinatura Eletrônica para Órgãos](https://www.gov.br/governodigital/pt-br/identidade/assinatura-eletronica/assinatura-eletronica-para-orgaos/assinatura-eletronica-para-orgaos)
descreve integração para órgãos públicos e determina que a solicitação seja
formalizada por agente público. Ela não comprova acesso direto para a clínica
privada nem demonstra, por si só, que toda integração indireta seja impossível.
A [Portaria SGD/MGI 7.076/2024](https://www.in.gov.br/en/web/dou/-/portaria-sgd/mgi-n-7.076-de-2-de-outubro-de-2024-*-589504963)
trata da integração de serviços públicos digitais e estabelece condições para seu
escopo. Confirmar o enquadramento aplicável antes de assumir disponibilidade.

O [manual técnico oficial](https://manual-integracao-assinatura-eletronica.servicos.gov.br/pt-br/latest/iniciarintegracao.html)
descreve credenciais previamente autorizadas, OAuth, consentimento do signatário,
assinatura de hash e obtenção de certificado. Login gov.br, por si só, não é
assinatura. Uma simulação, TOTP ou booleano local não constituem evidência válida.

## Verificações históricas (não são pré-requisitos da decisão atual)

1. Confirmar junto ao canal oficial a elegibilidade e o caminho de integração para
   clínica privada, inclusive eventual uso por intermediário autorizado. Não há
   solicitação enviada por este projeto.
2. Obter, se disponível e autorizado, condições de homologação, credenciais, regras
   de uso, custos e permissão de tratamento de dados de saúde.
3. Validar juridicamente o tipo de assinatura e a evidência necessários para cada
   categoria profissional. A matriz CFP/COFFITO continua pendente.
4. Só então concluir o adaptador real, vincular a identidade do signatário ao autor,
   conferir documento e evidência no servidor e testar falhas, replay e auditoria.

O portal público de assinatura pelo cidadão e a API de integração são modalidades
diferentes. A existência do portal não demonstra autorização para integração
programática nem que o fluxo manual seja adequado ao prontuário.
