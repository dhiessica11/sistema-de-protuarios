# Modelos adicionais: registro por tentativa e CAA

Levantamento de três arquivos enviados pela clínica: `A- REGISTRO NOVO.xlsx`,
`CAA_DAGG3_Espaco_Desenvolver_MODELO.xlsx` e `REGISTRO PARA IMPRIMIR 2.pdf`.
Este documento descreve requisitos e verificações; a seção de estado atual distingue
o fluxo experimental já implementado dos demais itens pendentes.
Os arquivos e seu conteúdo clínico não devem ser incluídos no repositório.

## Registro por tentativa

O modelo Excel tem três folhas de registro e três de gráfico. Cada folha de
registro associa paciente, programa e aplicador a data, atividade e até 15
marcações de tentativa por linha. As opções identificadas são I, G, VP, VT, FP,
FT, VS e E. As fórmulas calculam percentuais de erro, de ajuda e de independência
sobre as células de tentativa preenchidas. A classificação de cada código e as
regras de preenchimento devem ser confirmadas com a clínica.

O PDF contém duas páginas de formulário, com campos de paciente, programa,
atividade, frequência, dez tentativas, data e legenda de apoios. A quantidade
máxima difere da planilha; não assumir equivalência entre os dois formatos ou
impor um limite único sem decisão da clínica. A extração de texto do PDF reportou
erros de compressão, portanto a leitura deve ser conferida visualmente antes de
reproduzir integralmente seus campos ou apresentação.

O fluxo experimental registra sessão, profissional, paciente e, opcionalmente,
um objetivo de plano do mesmo paciente, data, atividade, observações e até 100
tentativas. Apresenta contagens e percentuais por tentativa: I como independente,
E como erro e os demais códigos como ajuda, conforme a fórmula da planilha. Sem
tentativas, os percentuais ficam ausentes e a tela informa «sem dados». O modelo
Excel retorna zero nesse caso: a mudança proposta e a interpretação dos códigos
devem ser validadas com a clínica. O PostgreSQL protege os registros contra
alteração ou exclusão, sujeito às limitações de privilégio descritas abaixo.

## CAA / DAGG-3

A planilha tem 20 abas, incluindo uma base de metas oculta. O guia descreve:

1. Perfil inicial: sistema de CAA, acesso e perfil comunicativo.
2. Avaliação por competências linguística, operacional, social e estratégica;
   cada meta recebe marcação em progresso (MP), atingida (MA) ou não aplicável,
   além do nível de apoio quando pertinente. Meta sem marcação é não avaliada.
3. Sugestões e revisão profissional; plano CAA com objetivos, apoios, critérios,
   estratégias, contextos, orientações e datas.
4. Sessões por função ou objetivo: oportunidades reais, respostas por nível de
   apoio, mensagens, parceiros, ambientes, modelos e observações. Sem resposta é
   uma categoria calculada; a planilha informa que não é falha.
5. Resumo por função, painel semanal e reavaliação com preservação histórica.

O guia atribui o DAGG-3 a Tobii Dynavox e Vicki Clarke e cita uma adaptação da
planilha. Antes de reproduzir metas, textos oficiais, tabelas ou traduções no
produto, confirmar licença e permissão aplicáveis. A posse do arquivo, por si só,
não comprova autorização de reprodução. Até essa confirmação, trabalhar com
itens e cenários sintéticos, sem transcrever o conteúdo protegido para o código.

### Regras que precisam de revisão

- A pessoa responsável pelo projeto determinou que cada dificuldade identificada
  gere uma proposta para revisão pela fonoaudióloga. O modelo CAA prioriza metas
  em progresso e limita o número de sugestões. Confirmar como essa priorização
  deve coexistir com a criação de uma proposta para cada dificuldade, sem tratar
  itens não avaliados ou não aplicáveis como dificuldades.
- Os valores 7 em 10, 3 sessões, limiar de 80% para nível e prazos são parâmetros
  configuráveis da clínica, apresentados como critérios internos, não normas do
  DAGG-3. Não transformá-los em padrões clínicos universais.
- A descrição do objetivo sugere 7 em 10 em 3 sessões consecutivas. No modelo,
  o status `Plano CAA!L17` verifica o percentual agregado `K17` e a contagem de
  linhas `J17`, sem demonstrar três sessões consecutivas individualmente no
  critério. Confirmar o comportamento clínico desejado antes de automatizar
  «critério atingido» e testá-lo com sequências que não sejam consecutivas.
- Em `Registro de sessão`, o campo calculado de sem resposta usa oportunidades
  menos respostas, limitado a zero; a coluna de verificação sinaliza respostas
  maiores que oportunidades. No sistema, validar a inconsistência na entrada e
  não ocultá-la; distinguir zero, ausência de dados e item não aplicável.
- Não somar ou comparar instrumentos, níveis de apoio ou funções distintas como
  se fossem medidas equivalentes. Gráficos e indicadores devem indicar período,
  denominador, critérios configurados e dados insuficientes; relatórios e decisões
  precisam de revisão profissional antes de uso ou compartilhamento.

## Relação com o estado atual

O projeto possui fluxos experimentais de avaliação por texto, propostas
revisáveis, planos com metas e sessões por tentativa para dados fictícios. Ainda
agora apresenta evolução diária por objetivo para sessões de tentativas, em períodos
de até 366 dias e até 1000 sessões. Os percentuais de cada dia usam o total das
tentativas registradas naquele dia, não a média dos percentuais das sessões. Dias
com sessões sem tentativas mostram dados ausentes; não são gerados dias sem sessão.
A visualização não determina aquisição ou diagnóstico. Ainda não implementa itens
DAGG-3, suas escalas, indicadores de CAA, impressão dos formulários ou integração
com as planilhas. O módulo de assinatura
ICP-Brasil e os controles para produção continuam pendentes.

A interface de sessões apresenta objetivos dos planos na página atual do histórico
de planos; navegue até outra página para selecionar um objetivo antigo. A API exige
fonoaudióloga vinculada ao paciente; a assinatura é informada como ausente. Textos
e tentativas são cifrados. SQLite não aplica as triggers; owner ou superusuário do
PostgreSQL pode desativá-las. A interface e API estão restritas ao desenvolvimento.

Próximos incrementos: validar CAA, suas regras e licenças com a responsável e
desenvolver seus indicadores e relatórios, sem apresentar critérios de aquisição
como diagnósticos. Na visualização atual, somente objetivos da página atual de
planos são listados; a mudança de objetivo ou período limpa os resultados anteriores.
