# Admin Studio - Sistema de Gestão Escolar

O **Admin Studio** é uma plataforma completa e moderna de gestão escolar desenvolvida em Django. Projetado para estúdios de dança, academias e escolas de cursos livres, o sistema centraliza o controle financeiro, gestão de matrículas, controle de professores e agendamento de aulas em uma única interface elegante.

## 🚀 Tecnologias Utilizadas
* **Backend:** Python 3.11, Django 5.x
* **Frontend:** HTML5, Tailwind CSS (via django-tailwind), Lucide Icons (django-lucide)
* **Banco de Dados:** PostgreSQL (Configurável via Docker)
* **Infraestrutura:** Docker e Docker Compose para fácil implantação.

---

## 👥 Perfis de Acesso (Roles)
O sistema opera com uma arquitetura multi-tenant (múltiplas escolas) e controle de acesso baseado em papéis (Role-Based Access Control):
* **Administrador (ADMIN_ESCOLA):** Acesso total ao painel da sua respectiva escola. Pode matricular alunos, cadastrar professores, gerenciar o financeiro e administrar todas as aulas.
* **Professor (PROFESSOR):** Acesso à visualização de sua própria grade de aulas, lista de alunos confirmados por aula e gestão do que foi lecionado.
* **Aluno (ALUNO):** Acesso ao calendário de aulas disponíveis no seu plano e sistema de auto-reserva (check-in) em horários.

---

## 🧩 Módulos e Regras de Negócio

### 1. Gestão de Alunos e Matrículas
* **Cadastro Completo:** Coleta de dados pessoais (Nome, E-mail, CPF, Telefone, Data de Nascimento). A idade do aluno é calculada e mantida atualizada automaticamente.
* **Matrículas e Planos:** Todo aluno é vinculado a um **Plano** (mensalidade recorrente) ou **Pacote** (quantidade fixa de aulas).
* **Vencimentos:** O administrador define o "Dia de Vencimento" no ato da matrícula.
* **Status Ativo/Inativo:** Alunos podem ter suas matrículas desativadas. **Regra de Negócio:** Alunos inativos têm o acesso bloqueado para reservar novas aulas e ficam visualmente marcados no sistema.

### 2. Gestão de Professores e Folha de Pagamento
* **Perfil do Docente:** Cadastro de dados pessoais de contato e acesso próprio.
* **Contratos Flexíveis:**
    * **Fixo Mensal:** Salário pré-estabelecido independentemente da quantidade de aulas.
    * **Por Hora/Aula:** O sistema projeta automaticamente o salário mensal baseado na quantidade de horários fixos que o professor possui na grade da escola.
* **Dia de Pagamento:** Cada professor possui um dia de vencimento configurável para recebimento do salário.

### 3. Grade de Aulas e Agendamentos
* **Aulas Regulares:** O administrador cadastra aulas definindo a disciplina (Categoria), o Professor responsável, a faixa etária permitida, vagas máximas e o cronograma semanal recorrente.
* **Sistema de Reservas (Check-in):** 
    * Alunos só podem reservar aulas disponíveis para seus planos.
    * **Lista de Espera Inteligente:** Se a aula atinge a lotação máxima (`vagas_max`), os próximos alunos entram em status de `ESPERA`.
    * **Promoção Automática:** Se um aluno com vaga `CONFIRMADO` cancelar a reserva, o sistema automaticamente promove o primeiro aluno da lista de espera e o notifica.
* **Overrides (Alterações Pontuais):** Permite que uma aula específica em uma data exata seja **Cancelada** ou que o professor titular seja substituído por um **Professor Substituto**, sem afetar a recorrência fixa do calendário.

### 4. Controle Financeiro
O coração do negócio, garantindo previsibilidade e rastreabilidade:
* **Mensalidades (Receitas):**
    * Exibição das mensalidades geradas, com possibilidade de anexar o comprovante de pagamento (ex: recibo PIX).
    * **Atualização Automática:** Mensalidades pendentes que ultrapassam a data de vencimento são automaticamente migradas para o status **ATRASADO** sempre que o sistema é acessado.
    * **Quitação em Lote:** É possível liquidar várias mensalidades de um plano de uma única vez.
    * **Automação de Status:** Ao inserir a data de pagamento em uma fatura pendente, o sistema inteligentemente a marca como **PAGA**. Se a data for removida, o status reverte de forma segura.
* **Despesas:**
    * **Lançamentos Avulsos:** Despesas fixas ou pontuais (Aluguel, Luz, Figurinos, Eventos).
    * **Integração com Professores:** O painel financeiro projeta automaticamente a folha de pagamento dos professores na lista de despesas previstas do mês atual, evitando surpresas no caixa.

### 5. Dashboard Gerencial
A página inicial (`HomeView`) fornece indicadores-chave de desempenho em tempo real:
* Contagem de alunos ativos.
* Receita estimada do ciclo atual (Baseada na soma de todos os contratos vigentes).
* Número de aulas acontecendo "hoje" (já contabilizando cancelamentos ou reposições pontuais do dia).
* Alertas de planos e pacotes vencendo nos próximos 7 dias.

---

## 🛠️ Como Executar o Projeto

1. **Clone o repositório:**
   ```bash
   git clone https://github.com/olheolie/admin_studio.git
   cd admin_studio
   ```

2. **Suba os containers (Banco de Dados):**
   *(Se estiver utilizando Docker)*
   ```bash
   docker-compose up -d
   ```

3. **Instale as dependências:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Aplique as Migrações:**
   ```bash
   python manage.py migrate
   ```

5. **Inicie o Servidor Local:**
   ```bash
   python manage.py runserver
   ```
   *O painel estará disponível em `http://localhost:8000`*

## 🎨 Estilização Dinâmica (Tailwind)
Para compilar o Tailwind durante o desenvolvimento, utilize a integração nativa em uma aba separada do terminal:
```bash
python manage.py tailwind start
```
