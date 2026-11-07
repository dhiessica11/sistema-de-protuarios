# Impressão digital interna experimental

A função `impressao_digital_registro` calcula SHA-256 do estado persistido de um
Registro, com serialização JSON UTF-8 versionada e ordem de chaves estável. Inclui
os identificadores, categoria histórica, tipo, origem, texto, resumo, justificativa,
contato, compartilhamento e data em UTC. Busca o estado no banco pelo identificador;
alterações não salvas em memória não mudam o resultado. Alteração do conjunto de
campos do model interrompe o cálculo até revisão explícita da representação.

O cálculo é interno, sem endpoint, persistência do hash, chamada ao gov.br ou mudança
no estado `sem_assinatura`. Seu valor deve ser tratado como informação sensível. O
chamador futuro precisa verificar identidade e vínculo antes de consultar o registro.

**Não é assinatura, PDF, comprovante nem integração com gov.br.** O formato real a
assinar ainda precisa ser definido após confirmar as regras do provedor e o processo
clínico. Esta representação inclui IDs, mas não preserva os dados de identificação
ou registro profissional tal como exibidos em documento; também referencia a origem
por ID, sem comprovar o conteúdo da cadeia anterior. Esses pontos devem ser resolvidos
antes de qualquer assinatura. Uma impressão digital não comprova que o profissional
viu ou aprovou o conteúdo, nem valida certificado, identidade ou integridade no tempo.

A seleção do mecanismo e a integração ICP-Brasil continuam pendentes:
veja `assinatura-icp-brasil.md`. Não usar a função como evidência ou com dados reais.
