from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('login/', auth_views.LoginView.as_view(template_name='gestao/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # Aulas (Página padrão para aluno)
    path('aulas/', views.AulasListView.as_view(), name='aulas_lista'),
    path('aulas/minhas/', views.MinhasAulasView.as_view(), name='minhas_aulas'),
    path('aulas/<int:pk>/reservar/', views.ReservarAulaView.as_view(), name='reservar_aula'),
    path('aulas/<int:pk>/cancelar/', views.CancelarReservaView.as_view(), name='cancelar_reserva'),
    path('aulas/<int:pk>/reagendar/', views.AulaRescheduleView.as_view(), name='reagendar_aula'),
    path('aulas/<int:pk>/admin-reservar/', views.AdminReserveView.as_view(), name='admin_reservar_aula'),
    path('agendamento/<int:pk>/cancelar-admin/', views.AdminCancelAgendamentoView.as_view(), name='admin_cancelar_agendamento'),

    # Cadastros
    path('alunos/', views.AlunoListView.as_view(), name='aluno_lista'),
    path('alunos/<int:pk>/perfil/', views.AlunoUpdateView.as_view(), name='aluno_perfil'),
    path('cadastro/aluno/', views.AlunoCreateView.as_view(), name='cadastro_aluno'),
    path('professores/', views.ProfessorListView.as_view(), name='professor_lista'),
    path('professores/<int:pk>/perfil/', views.ProfessorUpdateView.as_view(), name='professor_perfil'),
    path('cadastro/professor/', views.ProfessorCreateView.as_view(), name='cadastro_professor'),
    path('cadastro/categoria/', views.CategoriaCreateView.as_view(), name='cadastro_categoria'),

    path('cadastro/aula/', views.AulaCreateView.as_view(), name='cadastro_aula'),
    path('cadastro/aula/<int:pk>/editar/', views.AulaUpdateView.as_view(), name='editar_aula'),
    path('cadastro/planos-pacotes/', views.PlanosPacotesCreateView.as_view(), name='cadastro_planos_pacotes'),
    path('plano/<int:pk>/editar/', views.PlanoUpdateView.as_view(), name='editar_plano'),
    path('pacote/<int:pk>/editar/', views.PacoteUpdateView.as_view(), name='editar_pacote'),
    path('plano/<int:pk>/excluir/', views.PlanoDeleteView.as_view(), name='excluir_plano'),
    path('pacote/<int:pk>/excluir/', views.PacoteDeleteView.as_view(), name='excluir_pacote'),

    
    # Gerenciamento
    path('gerenciar/escola/', views.EscolaInfoView.as_view(), name='escola_info'),
    # Financeiro
    path('financeiro/', views.FinanceiroGeralView.as_view(), name='financeiro_geral'),
    path('financeiro/aluno/<int:pk>/', views.AlunoFinanceiroView.as_view(), name='aluno_financeiro'),
    path('financeiro/pagamento/<int:pk>/editar/', views.PagamentoUpdateView.as_view(), name='editar_pagamento'),
    path('financeiro/despesa/nova/', views.DespesaCreateView.as_view(), name='nova_despesa'),
]
