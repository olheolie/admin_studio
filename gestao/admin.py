from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Escola, User, Aluno, Professor, Categoria, Plano, Pacote, Matricula, Aula, Agendamento

class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None, {'fields': ('role', 'escola', 'telefone', 'cpf', 'idade')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields': ('role', 'escola', 'telefone', 'cpf', 'idade')}),
    )

admin.site.register(User, CustomUserAdmin)
admin.site.register(Escola)
admin.site.register(Aluno)
admin.site.register(Professor)
admin.site.register(Categoria)
admin.site.register(Plano)
admin.site.register(Pacote)
admin.site.register(Matricula)
admin.site.register(Aula)
admin.site.register(Agendamento)
