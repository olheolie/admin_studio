from django import forms
from .models import Aluno, User, Matricula, Escola, Plano, Pacote, Categoria, Professor, Aula, PagamentoAluno, DespesaEscola

from django.utils import timezone
import re
from django.core.exceptions import ValidationError

def validate_cpf_numbers(value):
    cpf = re.sub(r'\D', '', value)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    for i in range(9, 11):
        soma = sum((int(cpf[num]) * ((i+1) - num) for num in range(0, i)))
        digit = ((soma * 10) % 11) % 10
        if digit != int(cpf[i]):
            return False
    return True

class AlunoForm(forms.ModelForm):
    nome = forms.CharField(max_length=255)
    email = forms.EmailField()
    telefone = forms.CharField(max_length=20)
    cpf = forms.CharField(max_length=14)
    data_nascimento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    # Matricula fields
    plano = forms.ModelChoiceField(queryset=None, required=False)
    pacote = forms.ModelChoiceField(queryset=None, required=False)
    data_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), initial=lambda: timezone.now().date())
    dia_vencimento = forms.IntegerField(min_value=1, max_value=31, required=False, help_text="Se não preenchido, será o dia atual.")


    class Meta:
        model = Aluno
        fields = []

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este e-mail já está cadastrado no sistema.")
        return email

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if not validate_cpf_numbers(cpf):
            raise ValidationError("CPF inválido.")
        return re.sub(r'\D', '', cpf)

    def clean_telefone(self):
        telefone = re.sub(r'\D', '', self.cleaned_data.get('telefone'))
        if len(telefone) != 11:
            raise ValidationError("O telefone deve ter 11 dígitos (DDD + número).")
        return telefone

    def __init__(self, *args, **kwargs):
        escola = kwargs.pop('escola', None)
        super().__init__(*args, **kwargs)
        from .models import Plano, Pacote
        if escola:
            self.fields['plano'].queryset = Plano.objects.filter(escola=escola)
            self.fields['pacote'].queryset = Pacote.objects.filter(escola=escola)

    def save(self, commit=True, user=None, escola=None):
        # Create user
        username = self.cleaned_data['email']
        user = User.objects.create_user(
            username=username,
            email=self.cleaned_data['email'],
            password='mudar123',
            role='ALUNO',
            escola=escola,
            first_name=self.cleaned_data['nome'],
            telefone=self.cleaned_data['telefone'],
            cpf=self.cleaned_data['cpf'],
            data_nascimento=self.cleaned_data['data_nascimento']
        )
        # Calculate age
        today = timezone.now().date()
        born = self.cleaned_data['data_nascimento']
        user.idade = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        user.save()
        
        aluno = Aluno.objects.create(user=user, escola=escola)
        
        # Create matricula
        from .models import Matricula
        vencimento = self.cleaned_data.get('dia_vencimento')
        if not vencimento:
            vencimento = timezone.now().day
            
        Matricula.objects.create(
            aluno=aluno,
            plano=self.cleaned_data.get('plano'),
            pacote=self.cleaned_data.get('pacote'),
            data_inicio=self.cleaned_data.get('data_inicio'),
            dia_vencimento=vencimento
        )

        return aluno

class PlanoForm(forms.ModelForm):
    class Meta:
        model = Plano
        fields = ['nome', 'categorias', 'duracao_meses', 'valor']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-ui-input border border-ui-border rounded-xl focus:ring-2 focus:ring-brand-primary outline-none transition-all'}),
            'duracao_meses': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 bg-ui-input border border-ui-border rounded-xl focus:ring-2 focus:ring-brand-primary outline-none transition-all'}),
            'valor': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 bg-ui-input border border-ui-border rounded-xl focus:ring-2 focus:ring-brand-primary outline-none transition-all'}),
            'categorias': forms.CheckboxSelectMultiple(),
        }


    def __init__(self, *args, **kwargs):
        self.escola = kwargs.pop('escola', None)
        super().__init__(*args, **kwargs)
        if self.escola:
            self.fields['categorias'].queryset = Categoria.objects.filter(escola=self.escola)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.escola:
            instance.escola = self.escola
        if commit:
            instance.save()
            self.save_m2m()
        return instance

class PacoteForm(forms.ModelForm):
    class Meta:
        model = Pacote
        fields = ['nome', 'quantidade_aulas', 'valor']
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-ui-input border border-ui-border rounded-xl focus:ring-2 focus:ring-brand-purple outline-none transition-all'}),
            'quantidade_aulas': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 bg-ui-input border border-ui-border rounded-xl focus:ring-2 focus:ring-brand-purple outline-none transition-all'}),
            'valor': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 bg-ui-input border border-ui-border rounded-xl focus:ring-2 focus:ring-brand-purple outline-none transition-all'}),
        }


    def __init__(self, *args, **kwargs):
        self.escola = kwargs.pop('escola', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        instance = super().save(commit=False)
        if self.escola:
            instance.escola = self.escola
        if commit:
            instance.save()
        return instance

class ProfessorForm(forms.ModelForm):
    nome = forms.CharField(max_length=255)
    email = forms.EmailField()
    telefone = forms.CharField(max_length=20)
    cpf = forms.CharField(max_length=14)
    data_nascimento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    tipo_salario = forms.ChoiceField(choices=Professor.TIPO_SALARIO_CHOICES, initial='FIXO')
    valor_salario = forms.DecimalField(max_digits=10, decimal_places=2, initial=0)
    dia_pagamento = forms.IntegerField(min_value=1, max_value=31, initial=5)

    class Meta:
        model = User
        fields = ['nome', 'email', 'telefone', 'cpf']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este e-mail já está cadastrado no sistema.")
        return email

    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if not validate_cpf_numbers(cpf):
            raise ValidationError("CPF inválido.")
        return re.sub(r'\D', '', cpf)

    def save(self, commit=True, escola=None):
        user = User.objects.create_user(
            username=self.cleaned_data['email'],
            email=self.cleaned_data['email'],
            password='mudar123',
            role='PROFESSOR',
            escola=escola,
            first_name=self.cleaned_data['nome'],
            telefone=self.cleaned_data['telefone'],
            cpf=self.cleaned_data['cpf'],
            data_nascimento=self.cleaned_data['data_nascimento']
        )
        # Calculate age
        today = timezone.now().date()
        born = self.cleaned_data['data_nascimento']
        user.idade = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        user.save()
        
        Professor.objects.create(
            user=user, 
            escola=escola,
            tipo_salario=self.cleaned_data['tipo_salario'],
            valor_salario=self.cleaned_data['valor_salario'],
            dia_pagamento=self.cleaned_data['dia_pagamento']
        )
        return user

class ProfessorUpdateForm(forms.ModelForm):
    nome = forms.CharField(max_length=255)
    telefone = forms.CharField(max_length=20)
    cpf = forms.CharField(max_length=14)
    data_nascimento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    email = forms.EmailField()
    tipo_salario = forms.ChoiceField(choices=Professor.TIPO_SALARIO_CHOICES)
    valor_salario = forms.DecimalField(max_digits=10, decimal_places=2)
    dia_pagamento = forms.IntegerField(min_value=1, max_value=31)

    class Meta:
        model = Professor
        fields = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['nome'].initial = self.instance.user.first_name
            self.fields['telefone'].initial = self.instance.user.telefone
            self.fields['cpf'].initial = self.instance.user.cpf
            if self.instance.user.data_nascimento:
                self.fields['data_nascimento'].initial = self.instance.user.data_nascimento
            self.fields['tipo_salario'].initial = self.instance.tipo_salario
            self.fields['valor_salario'].initial = self.instance.valor_salario
            self.fields['dia_pagamento'].initial = self.instance.dia_pagamento
            self.fields['email'].initial = self.instance.user.email

    def save(self, commit=True):
        professor = super().save(commit=False)
        user = professor.user
        
        user.first_name = self.cleaned_data['nome']
        user.telefone = self.cleaned_data['telefone']
        user.cpf = self.cleaned_data['cpf']
        user.data_nascimento = self.cleaned_data['data_nascimento']
        
        today = timezone.now().date()
        born = user.data_nascimento
        user.idade = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        user.save()
        
        professor.tipo_salario = self.cleaned_data['tipo_salario']
        professor.valor_salario = self.cleaned_data['valor_salario']
        professor.dia_pagamento = self.cleaned_data['dia_pagamento']
        
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']
        
        if commit:
            professor.save()
        return professor


class AulaForm(forms.ModelForm):
    class Meta:
        model = Aula
        fields = ['nome', 'categoria', 'professor', 'vagas_max', 'idade_min', 'idade_max']

    def __init__(self, *args, **kwargs):
        escola = kwargs.pop('escola', None)
        super().__init__(*args, **kwargs)
        if escola:
            self.fields['categoria'].queryset = Categoria.objects.filter(escola=escola)
            self.fields['professor'].queryset = Professor.objects.filter(escola=escola)

    def save(self, commit=True, escola=None):
        aula = super().save(commit=False)
        if escola:
            aula.escola = escola
        
        # Collect multiple slots from POST data
        # Note: self.data is QueryDict, so we use getlist()
        dias = self.data.getlist('dia_semana[]')
        inicios = self.data.getlist('hora_inicio[]')
        fims = self.data.getlist('hora_fim[]')
        
        horarios = {}
        for dia, inicio, fim in zip(dias, inicios, fims):
            if dia and inicio and fim:
                if dia not in horarios:
                    horarios[dia] = []
                horarios[dia].extend([inicio, fim])
        
        aula.horarios_json = horarios
        
        if commit:
            aula.save()
        return aula

class AlunoUpdateForm(forms.ModelForm):
    nome = forms.CharField(max_length=255)
    telefone = forms.CharField(max_length=20)
    cpf = forms.CharField(max_length=14)
    data_nascimento = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    
    # Matricula fields
    plano = forms.ModelChoiceField(queryset=None, required=False)
    data_inicio = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)
    dia_vencimento = forms.IntegerField(min_value=1, max_value=31, required=False)

    class Meta:
        model = Aluno
        fields = ['ativo']

    def __init__(self, *args, **kwargs):
        escola = kwargs.pop('escola', None)
        super().__init__(*args, **kwargs)
        from .models import Plano
        if escola:
            self.fields['plano'].queryset = Plano.objects.filter(escola=escola)
        
        if self.instance.pk:
            user = self.instance.user
            self.fields['nome'].initial = user.first_name
            self.fields['telefone'].initial = user.telefone
            self.fields['cpf'].initial = user.cpf
            self.fields['data_nascimento'].initial = user.data_nascimento
            
            matricula = self.instance.matricula_set.first()
            if matricula:
                self.fields['plano'].initial = matricula.plano
                self.fields['data_inicio'].initial = matricula.data_inicio
                self.fields['dia_vencimento'].initial = matricula.dia_vencimento


    def clean_cpf(self):
        cpf = self.cleaned_data.get('cpf')
        if not validate_cpf_numbers(cpf):
            raise ValidationError("CPF inválido.")
        return re.sub(r'\D', '', cpf)

    def save(self, commit=True):
        aluno = super().save(commit=False)
        user = aluno.user
        user.first_name = self.cleaned_data['nome']
        user.telefone = self.cleaned_data['telefone']
        user.cpf = self.cleaned_data['cpf']
        user.data_nascimento = self.cleaned_data['data_nascimento']
        
        # Recalculate age
        today = timezone.now().date()
        born = user.data_nascimento
        user.idade = today.year - born.year - ((today.month, today.day) < (born.month, born.day))
        user.save()
        
        # Update matricula
        matricula = aluno.matricula_set.first()
        if matricula:
            if self.cleaned_data.get('plano'):
                matricula.plano = self.cleaned_data['plano']
            if self.cleaned_data.get('data_inicio'):
                matricula.data_inicio = self.cleaned_data['data_inicio']
            if self.cleaned_data.get('dia_vencimento'):
                matricula.dia_vencimento = self.cleaned_data['dia_vencimento']
            matricula.save()
        
        if commit:
            aluno.save()
        return aluno

class PagamentoAlunoForm(forms.ModelForm):
    quantidade_parcelas = forms.IntegerField(min_value=1, initial=1, required=False)

    class Meta:
        model = PagamentoAluno
        fields = ['aluno', 'descricao', 'valor', 'data_vencimento', 'data_pagamento', 'status', 'forma_pagamento', 'comprovante']
        widgets = {
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}),
            'data_pagamento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        escola = kwargs.pop('escola', None)
        super().__init__(*args, **kwargs)
        if escola:
            self.fields['aluno'].queryset = Aluno.objects.filter(escola=escola)
            
        if self.instance and self.instance.pk and self.instance.matricula:
            # Encontrar quantas parcelas pendentes existem a partir desta
            pendentes = PagamentoAluno.objects.filter(
                matricula=self.instance.matricula,
                status__in=['PENDENTE', 'ATRASADO'],
                data_vencimento__gte=self.instance.data_vencimento
            ).count()
            if pendentes > 1:
                self.fields['quantidade_parcelas'].max_value = pendentes
                self.fields['quantidade_parcelas'].help_text = f"Existem {pendentes} parcelas pendentes (incluindo esta)."
            else:
                self.fields['quantidade_parcelas'].widget = forms.HiddenInput()

    def clean(self):
        cleaned_data = super().clean()
        data_pagamento = cleaned_data.get('data_pagamento')
        status = cleaned_data.get('status')
        data_vencimento = cleaned_data.get('data_vencimento')
        
        # Se informou data de pagamento, garante que o status seja PAGO
        if data_pagamento and status != 'PAGO':
            cleaned_data['status'] = 'PAGO'
        
        # Se removeu a data de pagamento mas o status ainda é PAGO, volta para PENDENTE ou ATRASADO
        elif not data_pagamento and status == 'PAGO':
            if data_vencimento and data_vencimento < timezone.now().date():
                cleaned_data['status'] = 'ATRASADO'
            else:
                cleaned_data['status'] = 'PENDENTE'
        
        return cleaned_data


    def save(self, commit=True):

        instance = super().save(commit=False)
        if commit:
            instance.save()
            
            # Se pagar múltiplas parcelas
            qtd = self.cleaned_data.get('quantidade_parcelas', 1)
            if qtd and qtd > 1 and instance.status == 'PAGO':
                proximas = PagamentoAluno.objects.filter(
                    matricula=instance.matricula,
                    status__in=['PENDENTE', 'ATRASADO'],
                    data_vencimento__gt=instance.data_vencimento
                ).order_by('data_vencimento')[:qtd-1]
                
                for pgto in proximas:
                    pgto.status = 'PAGO'
                    pgto.data_pagamento = instance.data_pagamento
                    pgto.forma_pagamento = instance.forma_pagamento
                    if instance.comprovante:
                        pgto.comprovante = instance.comprovante
                    pgto.save()
        
        return instance


class DespesaEscolaForm(forms.ModelForm):
    class Meta:
        model = DespesaEscola
        fields = ['descricao', 'categoria', 'valor', 'data_vencimento', 'data_pagamento', 'status', 'tipo', 'comprovante']
        widgets = {
            'data_vencimento': forms.DateInput(attrs={'type': 'date'}),
            'data_pagamento': forms.DateInput(attrs={'type': 'date'}),
        }

