# Cadastro fictício pela interface de desenvolvimento

A conta admin no modo de dados fictícios pode usar **Novo paciente fictício** na
página inicial. Escolha uma clínica cadastrada, informe nome, data de nascimento e
sexo registrado; nome social e CPF são opcionais. Se não houver clínica, a tela
mostra um link para cadastrar uma clínica fictícia no Django Admin. O seletor exibe
as primeiras 25 clínicas; a instalação prevista é de clínica única.

Após salvar o paciente, a tela abre seu cadastro. Em **Adicionar responsável
fictício**, informe nome, CPF válido para teste e vínculo; telefone e e-mail são
opcionais. Marque responsável principal somente quando apropriado. O cadastro do
paciente e do responsável são operações separadas: se a segunda falhar, o paciente
continua cadastrado e o responsável pode ser incluído depois.

Os formulários aparecem apenas para admin na configuração explícita de desenvolvimento
com dados fictícios. Usam a API existente, que valida permissões e dados e registra o
usuário criador. A validação de CPF rejeita os onze dígitos repetidos. A interface
não gera CPF, não altera cadastros existentes e não habilita o uso com dados reais.
Se a conexão cair durante um salvamento, confira a lista antes de repetir: a gravação
pode ter sido concluída mesmo que a resposta não tenha chegado ao navegador.
