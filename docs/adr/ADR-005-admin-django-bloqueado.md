# ADR-005 — Admin Django bloqueado para models clínicos

**Atualização:** o model `Registro` também não é registrado no Admin Django.

**Data:** 2026-10-24
**Status:** Aceita

## Contexto

Django Admin é poderoso e produtivo, mas bypassa serializers DRF — e com eles, as validações de domínio (autor_id imutável, consentimento versionado, categoria compatível para retificação, etc).

## Decisão

**Django Admin disponível APENAS para:**
- Configurações do sistema
- Templates de documento
- Gerenciamento de usuários profissionais (criar, desativar — nunca editar nome/registro profissional)
- Visualização (read-only) de logs de auditoria
- Gerenciamento de modelos operacionais (não-clínicos)

**Django Admin BLOQUEADO para:**
- Paciente
- Responsável
- Consentimento
- Registro clínico
- Assinatura
- Qualquer dado protegido por CFFa 777 ou LGPD sensível

Bloqueio implementado via NÃO registrar o model no Admin.

Admin em produção exige **YubiKey obrigatório** (WebAuthn), nunca TOTP sozinho.

## Alternativas rejeitadas

- **Admin liberado:** risco inaceitável de bypass de validação em dados clínicos
- **Admin com permissões granulares:** complexo, fácil de errar na configuração
- **Admin customizado com overrides de save():** ainda bypassa serializers, superfície de bug alta

## Consequências

- Todo CRUD clínico vai pela UI própria desde Sprint 1
- Rosanita gerencia pacientes pela UI própria, não pelo Admin
- Admin é ferramenta de operações técnicas da Dhiéssica, não de uso diário
- Migração de dados iniciais exige comando de management customizado (não "digita no Admin")
