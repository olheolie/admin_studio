Tabelas:
Aluno - id (uuid), nome, telefone, email, idade, cpf, escola/filial
Escola - id, Nome, CNPJ, email, endereço,


Professor -
Escola (Matriz) -
(relacionada à matriz) Filial (ex: jusc trindade, jusc centro) - 
Categorias (ex: dança, circo, fortalecimento, acrobático) -
Aulas (as aulas estão relacionadas ás categorias, e professores) - 
Planos (relacionado às categorias) -
Pacotes (relacionado à quantidade de aulas) -
Matricula - Plano (aceita null), Pacote (aceita null), inicio do contrato, fim do contrato(se o campo pacote for preenchido, o campo fim pode ser nulo)





Tipos de usuário
--> User da Escola (admin)
--> user Filial
--> User Professor 
--> User Aluno

Página inicial deve conter um menu lateral com opções de acordo com seu tipo de acesso(usuário):

User admin
Filiais - visível apenas se houver filiais cadastrado no user da escola
Professores 
Alunos 
Aulas
planos e pacotes

user Filial = admin, mas sem Filiais

User aluno 
Meu Plano/Pacote - 
Aulas(deve ser a página padrão do user aluno) - Direcionado a página de aulas disponíveis na semana, a página deve ser como um calendário semanal, onde deve mostrar as aulas disponíveis para o aluno fazer
o aluno deve poder selecionar a aula e cadastrar seu nome na aula daquela semana, se a aula estiver lotada deve aparecer como lotada, mas ele ainda pode colocar seu nome na lista de espera se alguém desisitir até 30min antes 

User Professor 
Minhas Aulas (pág padrão do user professor) 
aulas -  



Regras: 
Na página do admin, opção de conceder aos alunos acesso as aulas de outras filiais ou não.
página de gerênciamento de Escola/Filiais
User Ecola tem acesso ás informações das filiais

User Escola
Páginas de cadastro de:
Aluno
Filial
Professor
Categoria 
Aula



Menu Filiais > drop down com todas as filiais
Ao selecionar uma delas, é direcionado para a página com as informações daquela Filial -> Alunos, Professores, Aulas, Categorias

A página de cadastro de aluno deve conter 
Uma seção de Informações pessoais:
Nome, email, telefone, cpf, idade
seção de informação da matrícula (pode ser atualizada a qualquer momento):
Tipo de plano/pacote - drop down com todos os planos/pacotes disponíveis
tipo de contrato - mensal, trimestral, semestral, anual
data de início, 
data de fim (ajuste automático de acordo com a data de início e tipo de contrato, se for um pacote o campo é não obrigatório)
obs: ao cadastrar um aluno ele fica vinculado à escola/filial do usuário administrativo que o cadastrou.

A página de cadastro de professores deve conter uma seção com suas informações pessoais, assim como a de alunos, mais a(s) aula(s) que oferece.
obs: se eu apagar um professor suas aulas não devem ser apagadas automáticamente.

página de cadastro de aulas deve conter
categoria da aula, professor que leciona (pode ser alterado à qualquer momento), horários (segunda e sexta dàs 19h às 20h por exemplo), quantidade máxima de alunos na aula, idade min ou máxima da aula

Cadastro de Filial
Mesmas informações da Escola/Matriz/Cede
Só pode ser cadastrada pela Cede, e está relacionada à Escola que a cadastrou

Tecnologias: Python/Django, tailwind, postgres, docker

### TODOS:
```Criar página de Planos e Pacotes. 
``` 
```Definir criação página de criação de usuário, e tipos de usuário e suas permissões```
```Definir página de aulas distinta para usuários do tipo aluno, e do tipo professor```
```Definir regra para página de filiais
```
```Criar página para excluir e editar categoria
``` 
```Criar página para excluir e editar aula
```
## A página de aulas do admin deve conter duas abas; uma para mostrar as aulas e as categorias cadastradas, e a outra mostrando o calendário de aulas da semana 

## A página de aulas do professor deve mostrar duas abas; uma com as aulas em que ele está cadastrado e a outra mostrando o calendário de aulas da semana 

## A página de aulas do aluno deve mostrar o calendário de aulas da semana


``` OLHAR O STYLES.CSS E VERIFICAR SE TEM ALGO QUE POSSA SER REMOVIDO OU ALTERADO```

```VER https://www.youtube.com/watch?v=ni1u1RFKAP8&t=891s VERIFICAR O TAILWIND E O DJANGO```