# ADR-007 — User model customizado com login por username

**Data:** 2026-11-02
**Status:** Aceita

## Contexto

Login por e-mail eh padrao em SaaS modernos, mas colaborador da clinica
pode nao ter e-mail (estagiario, auxiliar, visitante autorizado).

## Decisao

- `Usuario(AbstractUser)` em `apps/clinica/models.py`
- `USERNAME_FIELD = "username"`
- `REQUIRED_FIELDS = []` (nem email obrigatorio)
- Email continua como campo opcional para notificacoes
- `AUTH_USER_MODEL = "clinica.Usuario"` no settings
- Campos adicionais: tipo, CRFa/CRP/CREFITO, CPF cifrado, 2FA

## Consequencias

- Flexibilidade: cadastro sem email
- Portal do responsavel usa modelo separado (nao Usuario) - decisao futura
- Convite profissional (v0.5) pode gerar username automatico baseado em nome
