# Preparação do Lote 3: STRIDE e vínculo de responsável

Data: 2026-11-03. Base main v0.2.4, CI aprovado. Nenhuma migration foi alterada.

## Evidência e correção

Com dados sintéticos, um profissional vinculado ao paciente A conseguiu executar
PATCH em um responsável de A para associá-lo a B, fora da equipe. A API respondeu
200 e a mudança foi confirmada no banco. O controle de objeto avaliava a origem,
mas o serializer aceitava um novo paciente na atualização.

Regressão introduzida antes da correção: **3 falhas e 1 sucesso**. A falha ocorreu
para admin, profissional com acesso ao destino e profissional sem acesso ao destino.
Foi adotada a preservação do vínculo histórico na API para todos os perfis:
um responsável existente não muda de paciente; outro vínculo deve ser cadastrado
pelo fluxo administrativo. Campos de contato continuam atualizáveis e o mesmo
paciente pode ser reenviado no payload.

O serializer rejeita a troca com HTTP 400 e erro no campo paciente antes de salvar.
Essa proteção é na API; não é uma constraint de imutabilidade do banco. Permissões
por campo, troca de guarda e reset de portal continuam pendentes no modelo STRIDE.

## Validação local executada

Código da branch montado na imagem web validada da v0.2.4, mesmas dependências do
lock; configurações de teste com SQLite em memória. Nenhum dado real foi usado.

- **78 testes passaram**, cobertura **81,60%** (799 statements, 147 não cobertos).
- Ruff lint OK; 37 arquivos formatados.
- Migrations sem drift e migrate aplicado em banco vazio.
- Fonte e resultado local: `stride-vinculo-validacao-local.txt`.
- O CI da nova branch usa PostgreSQL 16; seu resultado deve ser consultado no PR.

O STRIDE foi revisado contra models, serializers, views, permissões, settings,
Compose e ADRs. Ele distingue riscos confirmados de controles futuros, define
fronteiras, inclui as seis categorias e documenta os limites de trigger, cifra,
autenticação e assinatura. Sua existência não fecha os riscos ainda não tratados.
