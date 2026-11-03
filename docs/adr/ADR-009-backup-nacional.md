# ADR-009 — Backup 100% nacional (MagaluCloud + Locaweb)

**Data:** 2026-11-02
**Status:** Aceita (reverte parte do ADR-001)

## Contexto

Review externa 2026-11-02 apontou contradicao: documento declara "dados 100% Brasil"
mas plano original de backup usava Backblaze B2 (EUA) + Wasabi (EUA).

Cifra client-side (age) MITIGA mas NAO elimina transferencia internacional:
- Metadados (nome do arquivo, timestamps, tamanho) vao em claro
- ANPD trata dado cifrado ainda como dado pessoal (cifra != anonimizacao)
- LGPD Art. 33 aplicavel

## Decisao

**Backup principal:** MagaluCloud Object Storage (Sao Paulo, S3-compativel)
**Espelho mensal:** Locaweb Storage (Sao Paulo, S3-compativel)
**Cifra client-side age:** MANTIDA (defesa em profundidade)

## Alternativas rejeitadas

- **Backblaze B2:** EUA, click-wrap em ingles, CLOUD Act americano
- **Wasabi:** EUA, mesmo problema
- **AWS S3 sa-east-1:** nacional mas AWS corp EUA = subprocessador fora
- **DBaaS managed:** ja descartado no historico anterior

## Consequencias

- Custo adicional ~R$ 15/mes (R$ 20,40 vs R$ 17 original) - trivial
- Resolve F6.4 do deep-research (transferencia internacional)
- Elimina necessidade de documentar salvaguardas Art. 33
- Facilita contrato de operador LGPD (modelos em portugues)
- Suporte em portugues 24/7

## Checklist contratual

| Item | Valor |
|---|---|
| Regiao fisica | Sao Paulo / Brasil |
| Transferencia internacional | NAO |
| Subprocessadores | MagaluCloud + Locaweb (ambos BR) |
| Contrato | Operador LGPD padrao em portugues |
| Metadados | Territorio nacional |
| Logs do provedor | Territorio nacional |
| Suporte | Brasil |
| Mecanismo de saida | API delete + clausula contratual eliminacao <=30 dias |
| Direito a auditoria | Previsto em contrato (relatorio anual) |

## Codigo

Mudanca minima - S3 SDK (`boto3`) continua, muda endpoint:

```python
# settings/prod.py
AWS_S3_ENDPOINT_URL = "https://br-se1.magaluobjects.com"
AWS_S3_REGION_NAME = "br-se1"
```

## Monitoramento

Revisitar anualmente se MagaluCloud ou Locaweb mudar politica de localizacao de dados.
