# usuarios/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, PasswordResetToken

# Define um "inline" para o UserProfile
class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfis de Usuário'
    # Melhora a UI para o campo ManyToManyField
    filter_horizontal = ('questoes_favoritas',)

# Define uma nova classe de Admin para o User que inclui o nosso inline
class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

# Cancela o registro do User Admin padrão do Django
admin.site.unregister(User)
# Registra o User novamente com a nossa classe de Admin customizada
admin.site.register(User, UserAdmin)


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    """
    Admin View para PasswordResetToken.
    Visão de apenas leitura para auditoria e depuração de tokens de reset de senha.
    Não permite criar, editar ou deletar para manter a segurança.
    """
    list_display = ('user', 'token', 'created_at', 'is_token_expired')
    search_fields = ('user__username',)
    readonly_fields = ('user', 'token', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True # Permite ver a tela de detalhes

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Expirado?', boolean=True)
    def is_token_expired(self, obj):
        return obj.is_expired()