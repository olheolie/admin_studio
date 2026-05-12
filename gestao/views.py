from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from .models import Escola, Aluno, Professor, Categoria, Aula, Agendamento, Matricula, User, Plano, Pacote, AulaOverride, Notificacao, PagamentoAluno, DespesaEscola
from .forms import AlunoForm, AlunoUpdateForm, PlanoForm, PacoteForm, ProfessorForm, ProfessorUpdateForm, AulaForm, PagamentoAlunoForm, DespesaEscolaForm
import datetime

class HomeView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        role = request.user.role
        if role == 'ALUNO':
            return redirect('aulas_lista')
        elif role == 'PROFESSOR':
            return redirect('minhas_aulas')
        elif role == 'ADMIN_ESCOLA':
            escola = request.user.escola
            today = timezone.now().date()
            # Atualiza pagamentos vencidos automaticamente
            PagamentoAluno.objects.filter(
                escola=escola,
                status='PENDENTE',
                data_vencimento__lt=today
            ).update(status='ATRASADO')
            # Stats calculation
            alunos_ativos = Aluno.objects.filter(escola=escola).count()
            
            # Estimated revenue (sum of active subscriptions)
            from django.db.models import Sum
            receita_estimada = Matricula.objects.filter(
                aluno__escola=escola,
                data_fim__gte=today
            ).aggregate(total=Sum('plano__valor'))['total'] or 0
            
            # Classes today
            # We need to map today's weekday name to match the JSON field keys
            weekday_map = {0: 'segunda', 1: 'terca', 2: 'quarta', 3: 'quinta', 4: 'sexta', 5: 'sabado', 6: 'domingo'}
            today_name = weekday_map[today.weekday()]
            
            # Count regular classes for today
            aulas_hoje_count = Aula.objects.filter(
                escola=escola,
                horarios_json__has_key=today_name
            ).count()
            
            # Adjust with overrides (remove classes moved out, add classes moved in)
            moved_out = AulaOverride.objects.filter(aula__escola=escola, data_original=today).count()
            moved_in = AulaOverride.objects.filter(aula__escola=escola, nova_data=today).count()
            aulas_hoje_total = aulas_hoje_count - moved_out + moved_in
            
            # Expiring soon (next 7 days)
            vencendo_logo = Matricula.objects.filter(
                aluno__escola=escola,
                data_fim__range=[today, today + datetime.timedelta(days=7)]
            ).count()
            
            context = {
                'alunos_ativos': alunos_ativos,
                'receita_estimada': receita_estimada,
                'aulas_hoje': aulas_hoje_total,
                'vencendo_logo': vencendo_logo,
            }
            return render(request, 'gestao/dashboard.html', context)
        return redirect('login')



class AulasListView(LoginRequiredMixin, ListView):
    model = Aula
    template_name = 'gestao/aulas_lista.html'
    context_object_name = 'aulas'

    def get_queryset(self):
        user = self.request.user
        queryset = Aula.objects.filter(escola=user.escola)
        
        # Filtros básicos
        tab = self.request.GET.get('tab', 'calendario')
        categoria_id = self.request.GET.get('categoria')
        professor_id = self.request.GET.get('professor')
        
        if categoria_id:
            queryset = queryset.filter(categoria_id=categoria_id)
        if professor_id:
            queryset = queryset.filter(professor_id=professor_id)
        
        # Professor vê suas aulas por padrão
        if user.role == 'PROFESSOR':
            queryset = queryset.filter(professor=user.prof_profile)

                
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        tab = self.request.GET.get('tab', 'calendario')
        context['current_tab'] = tab
        
        # Dados para filtros na Tab Lista
        context['categorias'] = Categoria.objects.filter(escola=user.escola)
        context['professores'] = Professor.objects.filter(escola=user.escola)
        context['alunos_lista'] = Aluno.objects.filter(escola=user.escola)
        
        # Calendário Semanal
        today = timezone.now().date()
        start_week = today - datetime.timedelta(days=today.weekday())
        dias_semana = []
        labels = ['segunda', 'terca', 'quarta', 'quinta', 'sexta', 'sabado']
        labels_br = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado']
        
        for i in range(6):
            date = start_week + datetime.timedelta(days=i)
            dias_semana.append({
                'name': labels[i],
                'label': labels_br[i],
                'date': date,
                'is_today': date == today
            })
        context['dias_semana'] = dias_semana

        # Mapeamento de aulas por dia com Overrides
        aulas_full = Aula.objects.filter(escola=user.escola)
        
        # Aplicar filtros também ao calendário se existirem
        categoria_id = self.request.GET.get('categoria')
        professor_id = self.request.GET.get('professor')
        if categoria_id:
            aulas_full = aulas_full.filter(categoria_id=categoria_id)
        if professor_id:
            aulas_full = aulas_full.filter(professor_id=professor_id)

        if user.role == 'PROFESSOR':
            aulas_full = aulas_full.filter(professor=user.prof_profile)

            
        calendar_data = {}
        for dia in dias_semana:
            day_aulas = []
            # Check for regular schedule
            for aula in aulas_full:
                if dia['name'] in aula.horarios_json:
                    # Check if there is an override FOR THIS DAY that moves it OUT
                    override_out = AulaOverride.objects.filter(aula=aula, data_original=dia['date']).exists()
                    if not override_out:
                        # Add regular instance
                        horarios = aula.horarios_json[dia['name']]
                        agendamentos = Agendamento.objects.filter(aula=aula, data=dia['date'])
                        day_aulas.append({
                            'aula': aula,
                            'horario': f"{horarios[0]} - {horarios[1]}",
                            'date': dia['date'],
                            'is_override': False,
                            'students_count': agendamentos.filter(status='CONFIRMADO').count(),
                            'students': agendamentos.filter(status='CONFIRMADO')
                        })
            
            # Check for overrides moving classes TO THIS DAY
            overrides_in = AulaOverride.objects.filter(nova_data=dia['date'])
            for ov in overrides_in:
                agendamentos = Agendamento.objects.filter(aula=ov.aula, data=dia['date'])
                day_aulas.append({
                    'aula': ov.aula,
                    'horario': ov.novo_horario.strftime('%H:%M'),
                    'date': dia['date'],
                    'is_override': True,
                    'students_count': agendamentos.filter(status='CONFIRMADO').count(),
                    'students': agendamentos.filter(status='CONFIRMADO')
                })
            
            # Sort by time
            day_aulas.sort(key=lambda x: x['horario'])
            calendar_data[dia['name']] = day_aulas
            
        context['calendar_data'] = calendar_data
        
        # Acesso do Aluno
        if user.role == 'ALUNO':
            # Matrícula ativa -> Planos -> Categorias permitidas
            matricula = Matricula.objects.filter(aluno=user.aluno_profile).first()
            if matricula and matricula.plano:
                allowed_categories = list(matricula.plano.categorias.values_list('id', flat=True))
                context['allowed_categories'] = allowed_categories
            else:
                context['allowed_categories'] = []
                
        return context

class AulaRescheduleView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def post(self, request, pk, *args, **kwargs):
        aula = get_object_or_404(Aula, pk=pk)
        data_original = request.POST.get('data_original')
        nova_data = request.POST.get('nova_data')
        novo_horario = request.POST.get('novo_horario')
        cancelada = request.POST.get('cancelada') == 'on'
        professor_substituto_id = request.POST.get('professor_substituto')
        
        override_data = {
            'aula': aula,
            'data_original': data_original,
            'cancelada': cancelada,
        }
        
        if nova_data:
            override_data['nova_data'] = nova_data
        if novo_horario:
            override_data['novo_horario'] = novo_horario
            
        if professor_substituto_id:
            override_data['professor_substituto_id'] = professor_substituto_id
            
        override = AulaOverride.objects.create(**override_data)
        
        # Notificar alunos agendados
        agendamentos = Agendamento.objects.filter(aula=aula, data=data_original)
        for ag in agendamentos:
            if cancelada:
                titulo = "Aula Cancelada"
                mensagem = f"A aula de {aula.categoria.nome} do dia {data_original} foi cancelada."
            else:
                titulo = "Alteração na Aula"
                mensagem = f"A aula de {aula.categoria.nome} do dia {data_original} sofreu alterações."
                if nova_data and novo_horario:
                    mensagem += f" Novo horário: {nova_data} às {novo_horario}."
                
            Notificacao.objects.create(
                user=ag.aluno.user,
                titulo=titulo,
                mensagem=mensagem
            )
            # Se mudou a data, atualiza o agendamento
            if not cancelada and nova_data:
                ag.data = nova_data
                ag.save()
            # Se foi cancelada, exclui ou marca como cancelado
            if cancelada:
                ag.delete() # Ou criar um status CANCELADO
                
        return redirect('aulas_lista')


class AdminReserveView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def post(self, request, pk, *args, **kwargs):
        aula = get_object_or_404(Aula, pk=pk)
        aluno_id = request.POST.get('aluno_id')
        aluno = get_object_or_404(Aluno, pk=aluno_id)
        
        if not aluno.ativo:
            messages.error(request, f"O aluno {aluno.user.first_name} está inativo e não pode realizar reservas.")
            return redirect('aulas_lista')
            
        data = request.POST.get('data')
        
        Agendamento.objects.get_or_create(aluno=aluno, aula=aula, data=data, defaults={'status': 'CONFIRMADO'})
        return redirect('aulas_lista')

class ReservarAulaView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        aula = get_object_or_404(Aula, pk=pk)
        aluno = request.user.aluno_profile
        
        if not aluno.ativo:
            messages.error(request, "Sua matrícula está inativa. Entre em contato com a administração para reativar seu acesso.")
            return redirect('aulas_lista')
            
        data_str = request.POST.get('data')
        data = datetime.datetime.strptime(data_str, '%Y-%m-%d').date() if data_str else timezone.now().date()
        
        # Lógica de reserva (checar vagas)
        vagas_preenchidas = Agendamento.objects.filter(aula=aula, data=data, status='CONFIRMADO').count()
        status = 'CONFIRMADO' if vagas_preenchidas < aula.vagas_max else 'ESPERA'
        
        Agendamento.objects.get_or_create(aluno=aluno, aula=aula, data=data, defaults={'status': status})
        return redirect('aulas_lista')

class CancelarReservaView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        agendamento = get_object_or_404(Agendamento, pk=pk, aluno=request.user.aluno_profile)
        aula = agendamento.aula
        data = agendamento.data
        
        agendamento.delete()
        
        # Se liberou vaga confirmada, promove o primeiro da lista de espera
        vagas_preenchidas = Agendamento.objects.filter(aula=aula, data=data, status='CONFIRMADO').count()
        if vagas_preenchidas < aula.vagas_max:
            proximo = Agendamento.objects.filter(aula=aula, data=data, status='ESPERA').order_by('created_at').first()
            if proximo:
                proximo.status = 'CONFIRMADO'
                proximo.save()
                
                # Notificar o aluno promovido
                Notificacao.objects.create(
                    user=proximo.aluno.user,
                    titulo="Vaga Confirmada!",
                    mensagem=f"Sua reserva na aula de {aula.categoria.nome} do dia {data} foi confirmada automaticamente."
                )
        
class AdminCancelAgendamentoView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def post(self, request, pk, *args, **kwargs):
        agendamento = get_object_or_404(Agendamento, pk=pk)
        aula = agendamento.aula
        data = agendamento.data
        
        agendamento.delete()
        
        # Se liberou vaga confirmada, promove o primeiro da lista de espera
        vagas_preenchidas = Agendamento.objects.filter(aula=aula, data=data, status='CONFIRMADO').count()
        if vagas_preenchidas < aula.vagas_max:
            proximo = Agendamento.objects.filter(aula=aula, data=data, status='ESPERA').order_by('created_at').first()
            if proximo:
                proximo.status = 'CONFIRMADO'
                proximo.save()
                
                # Notificar o aluno promovido
                Notificacao.objects.create(
                    user=proximo.aluno.user,
                    titulo="Vaga Confirmada!",
                    mensagem=f"Sua reserva na aula de {aula.categoria.nome} do dia {data} foi confirmada automaticamente pelo administrador."
                )
        
        messages.success(request, "Reserva cancelada com sucesso.")
        return redirect('aulas_lista')

class AlunoListView(LoginRequiredMixin, UserPassesTestMixin, ListView):

    model = Aluno
    template_name = 'gestao/aluno_lista.html'
    context_object_name = 'alunos'

    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def get_queryset(self):
        return Aluno.objects.filter(escola=self.request.user.escola).select_related('user')

class AlunoCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = AlunoForm
    template_name = 'gestao/aluno_lista.html' # Unified template
    success_url = reverse_lazy('aluno_lista')

    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_tab'] = 'cadastro'
        context['alunos'] = Aluno.objects.filter(escola=self.request.user.escola)
        context['planos'] = Plano.objects.filter(escola=self.request.user.escola)
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['escola'] = self.request.user.escola
        return kwargs

    def form_valid(self, form):
        escola = self.request.user.escola
        form.save(escola=escola)
        messages.success(self.request, "Aluno matriculado com sucesso!")
        return redirect(self.success_url)

class AlunoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Aluno
    form_class = AlunoUpdateForm
    template_name = 'gestao/aluno_lista.html'
    success_url = reverse_lazy('aluno_lista')

    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['escola'] = self.request.user.escola
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_tab'] = 'cadastro' 
        context['planos'] = Plano.objects.filter(escola=self.request.user.escola)
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Informações do aluno atualizadas com sucesso!")
        return redirect(self.success_url)

class ProfessorListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Professor
    template_name = 'gestao/professor_lista.html'
    context_object_name = 'professores'

    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def get_queryset(self):
        return Professor.objects.filter(escola=self.request.user.escola)

class ProfessorCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    form_class = ProfessorForm
    template_name = 'gestao/professor_lista.html' # Use the same template with tabs
    success_url = reverse_lazy('professor_lista')

    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_tab'] = 'cadastro'
        context['professores'] = Professor.objects.filter(escola=self.request.user.escola)
        return context

    def form_valid(self, form):
        escola = self.request.user.escola
        form.save(escola=escola)
        messages.success(self.request, "Professor cadastrado com sucesso!")
        return redirect(self.success_url)

class ProfessorUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Professor
    form_class = ProfessorUpdateForm
    template_name = 'gestao/professor_lista.html'
    success_url = reverse_lazy('professor_lista')

    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_tab'] = 'cadastro'
        context['professores'] = Professor.objects.filter(escola=self.request.user.escola)
        return context

    def form_valid(self, form):
        form.save()
        messages.success(self.request, "Professor atualizado com sucesso!")
        return redirect(self.success_url)

class CategoriaCreateView(LoginRequiredMixin, CreateView):
    model = Categoria
    fields = ['nome']
    template_name = 'gestao/cadastro_categoria.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        form.instance.escola = self.request.user.escola
        return super().form_valid(form)

class AulaCreateView(LoginRequiredMixin, CreateView):
    form_class = AulaForm
    template_name = 'gestao/cadastro_aula.html'
    success_url = reverse_lazy('aulas_lista')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['escola'] = self.request.user.escola
        return kwargs

    def form_valid(self, form):
        escola = self.request.user.escola
        form.save(escola=escola)
        messages.success(self.request, "Aula criada com sucesso!")
        return redirect(self.success_url)

class EscolaInfoView(LoginRequiredMixin, TemplateView):
    template_name = 'gestao/escola_info.html'

class AulaUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Aula
    form_class = AulaForm
    template_name = 'gestao/cadastro_aula.html'
    success_url = reverse_lazy('aulas_lista')

    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['escola'] = self.request.user.escola
        return kwargs

    def form_valid(self, form):
        escola = self.request.user.escola
        form.save(escola=escola)
        messages.success(self.request, "Aula atualizada com sucesso!")
        return redirect(self.success_url)

class MinhasAulasView(LoginRequiredMixin, ListView):
    model = Aula
    template_name = 'gestao/minhas_aulas.html'
    
    def get_queryset(self):
        if self.request.user.role == 'PROFESSOR':
            return Aula.objects.filter(professor=self.request.user.prof_profile)
        return Aula.objects.none()

class PlanosPacotesCreateView(LoginRequiredMixin, View):
    template_name = 'gestao/cadastro_planos_pacotes.html'

    def get(self, request, *args, **kwargs):
        escola = request.user.escola
        plano_form = PlanoForm(escola=escola)
        pacote_form = PacoteForm(escola=escola)
        planos = Plano.objects.filter(escola=escola)
        pacotes = Pacote.objects.filter(escola=escola)
        return render(request, self.template_name, {
            'plano_form': plano_form,
            'pacote_form': pacote_form,
            'planos': planos,
            'pacotes': pacotes,
        })

    def post(self, request, *args, **kwargs):
        tipo = request.POST.get('tipo_item')
        if tipo == 'PLANO':
            form = PlanoForm(request.POST, escola=request.user.escola)
            if form.is_valid():
                form.save()
                messages.success(request, "Plano criado com sucesso!")
                return redirect('home')
        else:
            form = PacoteForm(request.POST, escola=request.user.escola)
            if form.is_valid():
                form.save()
                messages.success(request, "Pacote criado com sucesso!")
                return redirect('home')
        
        # If invalid
        plano_form = PlanoForm(request.POST if tipo == 'PLANO' else None, escola=request.user.escola)
        pacote_form = PacoteForm(request.POST if tipo == 'PACOTE' else None, escola=request.user.escola)
        return render(request, self.template_name, {
            'plano_form': plano_form,
            'pacote_form': pacote_form,
            'tab': tipo,
            'planos': Plano.objects.filter(escola=request.user.escola),
            'pacotes': Pacote.objects.filter(escola=request.user.escola),
        })

class PlanoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Plano
    form_class = PlanoForm
    template_name = 'gestao/plano_form.html'
    success_url = reverse_lazy('cadastro_planos_pacotes')

    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['escola'] = self.request.user.escola
        return kwargs

class PacoteUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Pacote
    form_class = PacoteForm
    template_name = 'gestao/pacote_form.html'
    success_url = reverse_lazy('cadastro_planos_pacotes')

    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['escola'] = self.request.user.escola
        return kwargs

class PlanoDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def post(self, request, pk):
        plano = get_object_or_404(Plano, pk=pk, escola=request.user.escola)
        plano.delete()
        messages.success(request, "Plano excluído com sucesso!")
        return redirect('cadastro_planos_pacotes')

class PacoteDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def post(self, request, pk):
        pacote = get_object_or_404(Pacote, pk=pk, escola=request.user.escola)
        pacote.delete()
        messages.success(request, "Pacote excluído com sucesso!")
        return redirect('cadastro_planos_pacotes')



class FinanceiroGeralView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'gestao/financeiro_geral.html'

    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        escola = self.request.user.escola
        status_filter = self.request.GET.get('status')
        
        # Atualiza pagamentos vencidos automaticamente
        PagamentoAluno.objects.filter(
            escola=escola,
            status='PENDENTE',
            data_vencimento__lt=timezone.now().date()
        ).update(status='ATRASADO')
        
        pagamentos = PagamentoAluno.objects.filter(escola=escola)
        if status_filter:
            pagamentos = pagamentos.filter(status=status_filter)
        
        pagamentos = pagamentos.order_by('aluno', 'data_vencimento')
        
        # Filtra apenas o primeiro pagamento de cada aluno para não repeti-los na lista geral
        pagamentos_unicos = []
        alunos_vistos = set()
        for p in pagamentos:
            if p.aluno_id not in alunos_vistos:
                pagamentos_unicos.append(p)
                alunos_vistos.add(p.aluno_id)
        
        # Ordena a lista resultante por data de vencimento
        pagamentos_unicos.sort(key=lambda x: x.data_vencimento)
        
        context['pagamentos'] = pagamentos_unicos
        context['despesas'] = DespesaEscola.objects.filter(escola=escola).order_by('data_vencimento')
        context['professores'] = Professor.objects.filter(escola=escola)

        context['despesa_form'] = DespesaEscolaForm()
        context['current_tab'] = self.request.GET.get('tab', 'alunos')
        context['current_status'] = status_filter
        return context


class AlunoFinanceiroView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Aluno
    template_name = 'gestao/aluno_financeiro.html'
    context_object_name = 'aluno'

    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA' or self.request.user.aluno_profile == self.get_object()

    def get_context_data(self, **kwargs):
        # Atualiza pagamentos vencidos deste aluno automaticamente
        PagamentoAluno.objects.filter(
            aluno=self.object,
            status='PENDENTE',
            data_vencimento__lt=timezone.now().date()
        ).update(status='ATRASADO')
        
        context = super().get_context_data(**kwargs)
        pagamentos = PagamentoAluno.objects.filter(aluno=self.object).order_by('-data_vencimento')
        context['pagamentos'] = pagamentos
        context['proximo_vencimento'] = pagamentos.filter(status='PENDENTE').order_by('data_vencimento').first()
        return context


class PagamentoUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = PagamentoAluno
    form_class = PagamentoAlunoForm
    template_name = 'gestao/pagamento_form.html'
    
    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def get_success_url(self):
        return reverse_lazy('aluno_financeiro', kwargs={'pk': self.object.aluno.pk})

class DespesaCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = DespesaEscola
    form_class = DespesaEscolaForm
    success_url = reverse_lazy('financeiro_geral')
    
    def test_func(self):
        return self.request.user.role == 'ADMIN_ESCOLA'

    def form_valid(self, form):
        form.instance.escola = self.request.user.escola
        messages.success(self.request, "Despesa registrada com sucesso!")
        return super().form_valid(form)
