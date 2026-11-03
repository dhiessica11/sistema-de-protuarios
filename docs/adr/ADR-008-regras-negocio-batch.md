# ADR-008 — Regras de negocio decididas em bloco

**Data:** 2026-11-02
**Status:** Aceita

## Contexto

25 regras de negocio pendentes antes de implementar Lote 2+.
Decisao em bloco acelerou implementacao sem bloquear modelagem.

## Decisao

Documentadas no vault: `02-Pessoal/prontuario-espaco-desenvolver/15-regras-negocio-decididas.md`

Resumo das 6 CRITICAS que afetam o codigo diretamente:

1. **Faltas = 4 consecutivas** (nao cumulativas) + aviso na 2a e 3a + atraso >30min = falta
2. **Reagendamento no portal** so em v0.5+ (MVP = telefone)
3. **Revogacao de consentimento LGPD** nao apaga dados historicos (base muda para "tutela da saude" Art. 11 II f LGPD)
4. **Visibilidade entre categorias**: resumo compartilhado + detalhe privado da categoria
5. **Documentos**: atestado e laudo = autor; encaminhamento = qualquer; orientacoes = qualquer
6. **Idade**: minima 0 meses (prematuros); 12-17 anos exige consentimento do menor + principal; aos 18 paciente assume portal

## Impacto no Lote 2

Nenhuma mudanca estrutural - regras validadas sem bloqueio.

## Impacto nos proximos lotes

- Lote 3 (Registro) usa regra 4 (visibilidade), 10 (adendo vs retificacao)
- Lote 4 (Agenda) usa regras 1 (faltas), 2 (reagendamento MVP), 14 (disponibilidade), 15 (ferias), 17 (duracao), 20 (feriados)
- Lote 5 (Documentos) usa regra 5 (quem emite), 11 (nome social)
- Lote 6 (Portal) usa regra 3 (revogacao), 6 (12-17 anos), 13 (exportacao LGPD)

## Consequencias

- Modelagem avanca sem esperar aprovacao caso-a-caso
- Reversao exige nova sessao formal de revisao (nao mudar silenciosamente)
