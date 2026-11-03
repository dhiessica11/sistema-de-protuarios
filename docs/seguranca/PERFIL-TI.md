# Separação entre TI e administração da clínica

O papel TI não é mais considerado administrativo pela API. Mesmo com
`is_superuser=True`, não pode listar, ler ou alterar pacientes, responsáveis,
consentimentos, vínculos de equipe, registros, usuários ou clínica pela API v1.
O papel `admin` mantém o acesso administrativo previsto; profissionais seguem
sujeitos ao vínculo ativo, categoria e permissões por campo.

No Django Admin, a gestão de usuários exige o papel `admin` além das permissões
normais do Django. Isso bloqueia TI e profissionais de promover a própria conta ou
criar outra conta administrativa pela interface, mesmo se forem superusuários.
A escrita em Clínica no Django Admin também exige o papel `admin`; a visualização
dos dados institucionais segue as permissões normais do Django. A tela de login
permanece disponível para usuários anônimos.

`createsuperuser` cria TI por padrão. A inicialização da primeira conta admin exige
procedimento local separado, descrito em INSTALAR.md. Operações de infraestrutura
e acesso a um shell, banco ou chaves são privilégios diferentes da API e não estão
isolados por esta mudança. Uma pessoa com controle desses recursos pode contornar
as regras da aplicação; não caracterizar esse perfil como tecnicamente incapaz de
acessar dados clínicos.

Antes de aplicar esta mudança em uma instalação existente, confirme que existe
uma conta ativa com `tipo=admin`, `is_staff=True` e as permissões administrativas
necessárias. Se houver apenas um superusuário TI, ele perderá a gestão de usuários
pelo Admin. A inicialização pelo shell é uma operação privilegiada e deve ser
planejada com a pessoa responsável pela clínica.

O procedimento de acesso emergencial com aprovação, prazo e auditoria reforçada
continua pendente. Esta mudança não cria uma exceção automática nem substitui MFA,
roles restritas no PostgreSQL, segregação de segredos ou auditoria append-only.
Não habilita uso com dados reais. Veja `docs/validacao/perfil-ti.md`.
