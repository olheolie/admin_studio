import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class Escola(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=20, unique=True)
    email = models.EmailField()
    endereco = models.TextField()

    def __str__(self):
        return self.nome

class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN_ESCOLA', 'Admin Escola'),
        ('PROFESSOR', 'Professor'),
        ('ALUNO', 'Aluno'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    escola = models.ForeignKey(Escola, on_delete=models.SET_NULL, null=True, blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    cpf = models.CharField(max_length=14, unique=True, null=True, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    idade = models.PositiveIntegerField(null=True, blank=True)

class Categoria(models.Model):
    nome = models.CharField(max_length=100)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome

class Professor(models.Model):
    TIPO_SALARIO_CHOICES = (
        ('FIXO', 'Fixo Mensal'),
        ('HORA', 'Por Hora/Aula'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='prof_profile')
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)
    tipo_salario = models.CharField(max_length=10, choices=TIPO_SALARIO_CHOICES, default='FIXO')
    valor_salario = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    dia_pagamento = models.IntegerField(default=5)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    def get_salario_mensal(self):
        if self.tipo_salario == 'FIXO':
            return self.valor_salario
        else:
            # Estimativa básica: calcula quantas horas/aula o professor dá por semana e multiplica por 4 semanas.
            aulas = self.aulas_lecionadas.all()
            total_aulas_semana = 0
            for aula in aulas:
                horarios = aula.horarios_json
                if isinstance(horarios, dict):
                    for dia, horas in horarios.items():
                        # Cada par [inicio, fim] é uma aula (se bem formatado)
                        # Assumimos que cada entrada na lista `horas` (que é plana [inicio, fim]) representa uma aula.
                        # Ex: ["19:00", "20:00"] = 1 aula. len() // 2 = qtd aulas.
                        total_aulas_semana += len(horas) // 2
            
            # Aproximadamente 4 semanas no mês
            return self.valor_salario * total_aulas_semana * 4



class Aluno(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='aluno_profile')
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    @property
    def is_active(self):
        if not self.ativo:
            return False
        from django.utils import timezone
        today = timezone.now().date()
        matricula = self.matricula_set.first()
        if not matricula:
            return False
        
        # Se for plano mensal/anual
        if matricula.plano:
            if matricula.data_fim and matricula.data_fim >= today:
                return True
        
        # Se for pacote de aulas
        if matricula.pacote:
            # Aqui poderíamos checar se ainda tem aulas, mas por enquanto vamos considerar ativo se tiver matrícula
            return True
            
        return False

class Plano(models.Model):
    nome = models.CharField(max_length=100)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, null=True, blank=True)
    categorias = models.ManyToManyField(Categoria, related_name='planos')
    duracao_meses = models.PositiveIntegerField() # 1 para mensal, 3 trimestral, etc.
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.nome} - {', '.join([c.nome for c in self.categorias.all()])}"

class Pacote(models.Model):
    nome = models.CharField(max_length=100)
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, null=True, blank=True)
    quantidade_aulas = models.PositiveIntegerField()
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.nome} ({self.quantidade_aulas} aulas)"

class Matricula(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    plano = models.ForeignKey(Plano, on_delete=models.SET_NULL, null=True, blank=True)
    pacote = models.ForeignKey(Pacote, on_delete=models.SET_NULL, null=True, blank=True)
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    dia_vencimento = models.PositiveIntegerField(default=5)
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if self.plano and self.plano.duracao_meses and not self.data_fim:
            from datetime import timedelta
            self.data_fim = self.data_inicio + timedelta(days=30 * self.plano.duracao_meses)
        super().save(*args, **kwargs)
        
        if is_new:
            self.gerar_mensalidades()

    def gerar_mensalidades(self):
        from .models import PagamentoAluno
        import calendar
        import datetime
        
        if self.plano:
            for i in range(self.plano.duracao_meses):
                # Calcular vencimento
                month = self.data_inicio.month - 1 + i
                year = self.data_inicio.year + month // 12
                month = month % 12 + 1
                max_day = calendar.monthrange(year, month)[1]
                vencimento_dia = min(self.dia_vencimento, max_day)
                vencimento = datetime.date(year, month, vencimento_dia)
                
                # Se o vencimento calculado for menor que a data de início (no caso da matrícula ser feita depois do dia do vencimento),
                # empurramos o primeiro vencimento para o mês seguinte (opcional, mas comum).
                # Aqui vamos manter a regra de usar o vencimento do mês corrente mesmo que já tenha passado, vai cair como Atrasado ou Pendente de pagamento imediato.
                
                PagamentoAluno.objects.create(
                    aluno=self.aluno,
                    escola=self.aluno.escola,
                    matricula=self,
                    descricao=f"Mensalidade - {self.plano.nome} ({i+1}/{self.plano.duracao_meses})",
                    valor=self.plano.valor,
                    data_vencimento=vencimento,
                    status='PENDENTE'
                )
        elif self.pacote:
            # Para pacote, gera apenas um pagamento integral (ou dependendo da regra da escola).
            # Para este MVP, geramos 1 pagamento.
            vencimento_dia = min(self.dia_vencimento, calendar.monthrange(self.data_inicio.year, self.data_inicio.month)[1])
            vencimento = datetime.date(self.data_inicio.year, self.data_inicio.month, vencimento_dia)
            
            PagamentoAluno.objects.create(
                aluno=self.aluno,
                escola=self.aluno.escola,
                matricula=self,
                descricao=f"Pacote - {self.pacote.nome}",
                valor=self.pacote.valor,
                data_vencimento=vencimento,
                status='PENDENTE'
            )


class Aula(models.Model):
    nome = models.CharField(max_length=100, default="Nova Aula")
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)
    professor = models.ForeignKey(Professor, on_delete=models.SET_NULL, null=True, blank=True, related_name='aulas_lecionadas')
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)
    horarios_json = models.JSONField() # Ex: {"segunda": ["19:00", "20:00"], "sexta": ["19:00", "20:00"]}
    vagas_max = models.PositiveIntegerField()
    idade_min = models.PositiveIntegerField(default=0)
    idade_max = models.PositiveIntegerField(default=100)

    def __str__(self):
        return f"{self.nome} ({self.categoria.nome})"

    @property
    def percent_occupied(self):
        # This is a bit complex because it depends on the date, but for the list view we can just show a general one or latest.
        # However, it's better to calculate it per instance in the view.
        # But for compatibility with existing templates, I'll return a dummy or base it on something.
        return 0 

class Agendamento(models.Model):
    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE)
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE)
    data = models.DateField()
    status = models.CharField(max_length=20, choices=(('CONFIRMADO', 'Confirmado'), ('ESPERA', 'Lista de Espera')), default='CONFIRMADO')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('aluno', 'aula', 'data')

class AulaOverride(models.Model):
    aula = models.ForeignKey(Aula, on_delete=models.CASCADE, related_name='overrides')
    data_original = models.DateField()
    nova_data = models.DateField(null=True, blank=True)
    novo_horario = models.TimeField(null=True, blank=True)
    professor_substituto = models.ForeignKey(Professor, on_delete=models.SET_NULL, null=True, blank=True, related_name='aulas_substituidas')
    cancelada = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Notificacao(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificacoes')
    titulo = models.CharField(max_length=255)
    mensagem = models.TextField()
    lida = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class PagamentoAluno(models.Model):
    STATUS_CHOICES = (
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('ATRASADO', 'Atrasado'),
        ('CANCELADO', 'Cancelado'),
    )
    FORMA_PGTO_CHOICES = (
        ('PIX', 'PIX'),
        ('DINHEIRO', 'Dinheiro'),
        ('CARTAO_CREDITO', 'Cartão de Crédito'),
        ('CARTAO_DEBITO', 'Cartão de Débito'),
        ('BOLETO', 'Boleto'),
        ('TRANSFERENCIA', 'Transferência Bancária'),
    )

    aluno = models.ForeignKey(Aluno, on_delete=models.CASCADE, related_name='pagamentos')
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE)
    matricula = models.ForeignKey(Matricula, on_delete=models.SET_NULL, null=True, blank=True)
    descricao = models.CharField(max_length=255)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PGTO_CHOICES, null=True, blank=True)
    comprovante = models.FileField(upload_to='comprovantes/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.descricao} - {self.aluno} - {self.status}"

class DespesaEscola(models.Model):
    STATUS_CHOICES = (
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
    )
    TIPO_CHOICES = (
        ('MENSAL', 'Mensal (Fixa)'),
        ('PONTUAL', 'Pontual (Variável)'),
    )
    
    escola = models.ForeignKey(Escola, on_delete=models.CASCADE, related_name='despesas')
    descricao = models.CharField(max_length=255)
    categoria = models.CharField(max_length=100)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='PONTUAL')
    comprovante = models.FileField(upload_to='despesas/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.descricao} - R${self.valor} - {self.status}"

