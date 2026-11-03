# Assinatura gov.br: viabilidade da integração

Pesquisa inicial: 2026-11-03. Estado: **elegibilidade da clínica privada não
confirmada**. A decisão de exigir gov.br no v0 permanece; este documento registra
um risco de acesso técnico, sem substituí-la por outro fornecedor.

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

## Próximas verificações

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
