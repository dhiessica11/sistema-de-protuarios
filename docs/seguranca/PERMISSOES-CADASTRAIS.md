# Permissões de cadastro e fronteira com o Lote 3

> Para dados fictícios, a configuração explícita de desenvolvimento permite ao admin acessar e operar dados clínicos, mantendo autoria real. Essa exceção não é regra de produção.

**Atualização:** a API inicial de Registro agora aplica o acesso por categoria em
lista e detalhe. A tabela de Registro ao final registra os requisitos que orientaram
a implementação; exportação e tarefas clínicas seguem pendentes.

Data: 2026-11-03. Implementação das restrições de escrita em Paciente e Responsavel,
baseada no ADR-011. A política é verificada no servidor antes da validação de
valores e vale para PUT e PATCH. Leitura continua limitada ao vínculo ativo da equipe.

## Matriz implementada

| Operação / campos | Administração | Fono, TO ou psicologia com vínculo ativo |
|---|---|---|
| Cadastrar paciente | Permitido, status inicial padrão ativo | Proibido |
| Nome civil, CPF, nascimento, sexo, nacionalidade, naturalidade | Alterar com justificativa quando o valor mudar | Somente leitura |
| Endereço e telefone do paciente | Alterar | Somente leitura |
| Nome social do paciente | Cadastrar/alterar | Alterar |
| Status e data de encerramento | Somente leitura; não são campos de cadastro inicial | Alterar |
| Clínica de um paciente existente | Reenviar a mesma; transferência proibida | Somente leitura |
| Cadastrar/alterar responsável, contatos e campos de guarda | Permitido na API administrativa | Somente leitura, inclusive payload vazio |
| Nome/CPF do responsável | Alterar com justificativa quando o valor mudar | Somente leitura |
| Paciente de um responsável existente | Reenviar o mesmo; transferência proibida | Somente leitura |
| Vínculo de equipe | Permissão administrativa já existente | Ler apenas seus vínculos; sem escrita |
| Campos de autoria, hashes, timestamps e número de prontuário | Sem escrita pelo cliente | Sem escrita pelo cliente |

Usuário sem vínculo ativo não encontra o cadastro no queryset (404 no detalhe).
Fono, TO e psicologia têm os mesmos direitos sobre esses dados cadastrais comuns.
O perfil TI não é administrativo na API clínica. A restrição de interface não
isola quem tenha acesso direto ao banco e às chaves; o procedimento emergencial
auditado continua pendente. Ver `docs/seguranca/PERFIL-TI.md`.
Responsáveis ainda não têm autenticação/portal: a permissão futura de nome social
pelo responsável não está implementada nesta etapa.

Clínica e Usuário mantêm seus endpoints somente leitura. Consentimento mantém
o fluxo versionado existente; captura de evidência do aceite, timestamps confiáveis
e concorrência de versões continuam pendentes no STRIDE. Alterar um campo de guarda
administrativamente não equivale ao fluxo completo de troca de guarda: comprovação,
reset do futuro portal e demais verificações precisam ser implementados no seu lote.

## Contrato da API

- Campo conhecido sem permissão de escrita: HTTP 403, sem aplicar nenhuma parte
  do payload, mesmo que ele contenha também campos permitidos.
- Campo desconhecido ou tentativa de usar aliases internos, como `cpf_cifrado`
  e `cpf_hash`: HTTP 400. Não há atribuição em massa nem descarte silencioso.
- Identificação alterada sem motivo válido: HTTP 400 no campo
  `justificativa_alteracao`. Motivo: 10–2000 caracteres, sem espaços vazios.
- Nome/CPF com o mesmo valor lógico não requerem motivo; CPF com ou sem máscara
  é comparado pelo valor normalizado. Contatos não geram justificativa de identidade.
- Profissionais usam PATCH para atualizar seus campos; PUT completo de paciente
  continua sujeito aos campos obrigatórios do cadastro e à mesma autorização.
- CPF e nome do responsável continuam com os mesmos nomes públicos de entrada.
  Seus aliases agora persistem corretamente nos campos cifrados. Remover um CPF
  opcional de paciente limpa também o índice HMAC correspondente.

Exemplo administrativo de correção de identificação:

```json
{
  "nome_civil": "Nome corrigido",
  "justificativa_alteracao": "Correção cadastral conferida no documento apresentado."
}
```

## Persistência e concorrência

`AlteracaoCadastral`, criada por migration gerada pelo Django, registra paciente,
responsável quando aplicável, autor autenticado, instante do servidor, nomes dos
campos alterados e justificativa cifrada com a chave B. Não copia os valores antigos
e novos e não expõe motivo no JSON de resposta. Não há endpoint nem registro no Admin.

A atualização e a justificativa usam a mesma transação. O cadastro é relido com
`select_for_update` e validado novamente antes de salvar: um snapshot antigo não
pode dispensar motivo para uma mudança real nem restaurar um contato administrativo
antigo durante edição clínica. Falha na evidência reverte a alteração cadastral.

Isso não é a auditoria completa do Lote 7 nem proteção contra alteração por SQL,
owner do banco ou root. A autorização é da API. O registro de justificativa será
complementado pelos controles append-only e destino independente já previstos.

## Categorias: contrato para o futuro Registro

Não há texto clínico no modelo atual de cadastro a separar por categoria. A regra
do ADR-008 será aplicada quando Registro existir, em queryset e serializer:

| Leitura futura de Registro | Regra a implementar |
|---|---|
| Profissional da mesma categoria | Detalhe apenas com vínculo ativo e ação autorizada |
| Profissional de outra categoria | Apenas resumo explicitamente compartilhado; detalhe privado não deve sair do servidor |
| Administração | Permissões de cadastro não concedem autoria, assinatura ou leitura automática do detalhe clínico |
| TI | Sem acesso pelo endpoint clínico; acesso emergencial auditado e isolamento de infraestrutura permanecem pendentes |

Testes de lista, detalhe, exportação e tarefas por categoria serão necessários
com o modelo Registro. Não foi criado um helper sem consumidor para simular essa
proteção. TH08 permanece aberto. A captura histórica da categoria do autor também
permanece como requisito antes da primeira migration de Registro.

Testes executados e limitações em `docs/validacao/permissoes-cadastrais.md`.
