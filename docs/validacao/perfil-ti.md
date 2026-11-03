# Validação: perfil técnico e administração clínica

Data: 2026-11-03. Testes com dados sintéticos, código sobre a main após PR #5,
imagem de desenvolvimento v0.2.4 e PostgreSQL 16 isolado.

- **224 testes passaram**, cobertura **88,99%**.
- Ruff limpo, 50 arquivos formatados; migrations sem drift e aplicadas; Django
  system check sem problemas. Não há migration nova para a mudança de papel.
- Bandit no nível do CI: nenhum achado médio/alto.
- Superusuário TI recebeu 403 nos endpoints de clínica, usuários, pacientes,
  responsáveis, consentimentos, equipe e registros, inclusive detalhe/edição.
- No Django Admin, TI não pode listar, criar ou alterar usuários, acessar a troca
  de senha administrativa de usuários ou criar/alterar Clínica.
- Profissional com superusuário não pode alterar seu próprio perfil no Admin.
  Uma conta admin da clínica mantém acesso administrativo; login anônimo funciona.

Os testes do Admin usam storage estático de teste para não depender do manifesto
de `collectstatic`. O PR não altera a configuração estática de produção.

## Limites e implantação

Não foi implementado acesso emergencial nem aprovação/auditoria correspondente.
MFA, isolamento de banco/infraestrutura e proteção contra quem controla shell,
Docker ou chaves continuam pendentes. Essas restrições de API e Admin não impedem
um operador de infraestrutura privilegiado de acessar ou modificar dados por fora
da aplicação. Não considerar a separação completa ou pronta para dados reais.

`createsuperuser` continua criando TI. Instalações com apenas esse perfil precisam
provisionar uma conta `admin` autorizada antes de depender da gestão de usuários;
instruções em INSTALAR.md. Nenhum usuário existente é convertido automaticamente.
