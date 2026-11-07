# Avaliações e plano terapêutico em fonoaudiologia

## Origem e limites

Levantamento dos arquivos fornecidos pela clínica: modelo oficial v14.2.3 e uma
cópia com paciente fictício. Ambos têm 31 abas. Este documento registra requisitos;
nenhum protocolo, cálculo, importação ou plano foi implementado por ele. Não incluir
as planilhas nem dados de pacientes no repositório.

A aba «Como Preencher» avisa que as normas do ADL-2 e as referências ABFW foram
transcritas de fotos dos manuais e que a regra de cálculo dos itens ADL-2 foi
deduzida. A própria planilha solicita conferir os três pontos nos manuais físicos
antes do uso clínico. A análise não valida os cálculos, o conteúdo dos manuais ou
os direitos de reprodução e uso digital de protocolos de terceiros. Cada protocolo
precisa de validação clínica e verificação de permissão antes de ser disponibilizado.

## Fluxo desejado

1. Fonoaudióloga vinculada ao paciente inicia uma avaliação, registra data, protocolo,
   versão, itens aplicados, respostas e observações. Itens não aplicados permanecem
   distintos de respostas sem dificuldade ou de pontuação zero.
2. Uma reavaliação é outra aplicação datada, vinculada ao histórico do paciente e ao
   protocolo e versão correspondentes. A idade considerada é a da data de aplicação.
3. Após calcular apenas regras validadas para aquele protocolo, o sistema apresenta
   resultados rastreáveis e dificuldades identificadas. Um cálculo indisponível,
   entrada incompleta ou faixa fora do escopo não pode gerar conclusão de normalidade.
4. **Cada dificuldade identificada gera uma proposta de objetivo pendente de revisão.**
   Cada proposta mantém referência à dificuldade, avaliação, item ou regra de origem;
   dados manuais também devem identificar sua origem. O sistema não aprova objetivos.
5. A fonoaudióloga revisa cada proposta, pode ajustar a redação, priorizar ou justificar
   a não inclusão no plano. A dificuldade e a proposta original permanecem rastreáveis.
   A criação de propostas não equivale a plano aprovado nem a assinatura profissional.
6. O plano apresenta objetivos revisados, metas, prazos, recursos e orientações; sua
   versão e autoria devem ser preservadas. Mudanças posteriores ou reavaliações não
   substituem nem apagam avaliações e planos anteriores.
7. A evolução e os gráficos devem comparar apenas medidas compatíveis, com data,
   protocolo, versão, unidade, faixa aplicável e indicação de dados ausentes. Gráficos
   e relatórios para família são rascunhos sujeitos a revisão antes da divulgação.

A regra «cada dificuldade gera uma proposta» é uma decisão nova para o sistema.
A planilha atual combina sugestões automáticas com seleção e redação profissional;
ela não comprova que exista hoje uma proposta individual para cada dificuldade.

## Inventário da planilha

| Área | Abas ou instrumentos identificados |
|---|---|
| Linguagem | ADL-2, ABFW vocabulário e fonologia, PROC, Matriz de Comunicação, pragmática (aba nomeada PHAPERA / PAHPEA) |
| Fala e comunicação | GOAC, Sondagem AFI, Checklist Motor-Oral, Processador Gestalt |
| Outras medidas | PCRL, PAPL, avaliação neuropsicológica V.2, ABC e protocolo extra |
| Consolidação | Plano Terapêutico, Dificuldades PEI, gráficos, relatório de avaliação, relatório e gráficos para família, recebimento do plano |

Algumas abas de itens têm avaliação inicial e até cinco reavaliações; outras têm
limites diferentes. O sistema não deve assumir que todas compartilham a mesma
estrutura, escala ou contagem. A planilha identifica o plano como baseado na última
avaliação disponível por protocolo, enquanto a aba Dificuldades PEI indica síntese
da avaliação inicial. Essas diferenças precisam ser escolhidas explicitamente na
interface e preservadas como contexto no resultado.

## Requisitos de segurança e implantação

- Acesso exclusivo a fonoaudiólogas vinculadas ao paciente, com as mesmas regras de
  categoria e privacidade aplicadas aos registros clínicos. Não enviar texto privado
  a outras categorias, administração ou TI por listagens, exportações, gráficos ou logs.
- Dados clínicos cifrados, autorização no servidor, proteção contra alteração indevida,
  registro de autoria e trilha de auditoria. Assinatura ICP-Brasil continua futura.
- Arquivos originais não são importados automaticamente: definir previamente escopo,
  proteção contra arquivos maliciosos, privacidade, compatibilidade e validação de dados.
  Leitura de XLSX não recalcula fórmulas; valores armazenados podem estar ausentes ou
  desatualizados. Confrontar resultados com casos sintéticos conhecidos e revisão clínica.
- Validar fórmulas, dados de referência, idade e limites de cada protocolo com seus
  manuais, profissional responsável e casos de borda; registrar versão e procedência.
  Verificar licenças e autorização para reproduzir itens e tabelas de terceiros.
- Dados reais, relatórios externos e uso assistencial dependem dos controles de
  produção e validações clínica, profissional e jurídica ainda pendentes.

## Critérios do primeiro incremento

O primeiro protocolo será escolhido com a clínica. Entregar seu fluxo completo com
avaliação e reavaliação, dificuldade e proposta pendente, revisão pela fonoaudióloga,
histórico e testes de privacidade. Validar o comportamento com o exemplo fictício e
casos adicionais, antes de ampliar para outros protocolos. Definir separadamente se
fonIA é apenas referência ou se há integração autorizada e documentada; nenhum dado
será enviado ao serviço por esta proposta.
