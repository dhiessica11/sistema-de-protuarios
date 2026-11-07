# ADR-004 — Autoria imutável + retificação cria novo registro

**Atualização:** o vínculo e as validações de retificação/adendo estão implementados
para revisão, com registros identificados como `sem_assinatura`. A integração de assinatura qualificada ICP-Brasil permanece pendente; não
considerar a retificação clinicamente finalizada antes de assinatura verificável.

**Data:** 2026-10-24
**Status:** Aceita

## Contexto

CFFa 777/2025 Art. 3: autoria é indelegável. CFFa 777 Art. 14 permite retificação, mas registro original deve ser preservado para rastreabilidade e defesa jurídica.

## Decisão

**`REGISTRO.autor_id` é IMUTÁVEL**. Trigger Postgres nega UPDATE neste campo.

**Retificação NUNCA edita o registro original.** Cria um novo REGISTRO com:
- `retifica_id` → aponta para o original
- Nova assinatura do profissional que retifica
- Justificativa obrigatória (NOT NULL, min_length=50) incluindo quem foi contatado para validação
- Apenas profissional da **mesma categoria** pode retificar (fono retifica fono, não TO)

Timeline do paciente mostra:
- Registro original riscado + marcador "RETIFICADO"
- Registro novo logo abaixo, com link para o original

## Alternativas rejeitadas

- **Permitir edição com histórico de versões:** interface fica ambígua, risco de perder a defesa jurídica
- **Soft delete + novo registro:** mesmo problema, registro "apagado" perde o status jurídico
- **Qualquer categoria retifica qualquer:** viola a autonomia profissional entre áreas

## Consequências

- Autor "errado" por descuido = autor permanece, retificação explica
- Admin NÃO consegue "corrigir" autoria mesmo via Admin Django
- Interface de retificação precisa deixar MUITO claro que gera novo registro
- Testes de invariante OBRIGATÓRIOS cobrindo autor_id imutável + retificação só mesma categoria
