# usuarios/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile, PasswordResetToken, Ativacao

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Perfis de Usuário'
    filter_horizontal = ('questoes_favoritas',)
    raw_id_fields = ('avatar_equipado', 'borda_equipada', 'banner_equipado')

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'nome_completo', 'is_staff', 'is_superuser', 'is_active', 'date_joined')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    
    @admin.display(description='Nome Completo', ordering='userprofile__nome')
    def nome_completo(self, obj):
        if hasattr(obj, 'userprofile'):
            return f"{obj.userprofile.nome} {obj.userprofile.sobrenome}"
        return "N/A"

# Registra usando o admin.site padrão
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'is_token_expired')
    search_fields = ('user__username',)
    readonly_fields = ('user', 'token', 'created_at')
    ordering = ('-created_at',)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return True
    @admin.display(description='Expirado?', boolean=True)
    def is_token_expired(self, obj): return obj.is_expired()

@admin.register(Ativacao)
class AtivacaoAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'created_at', 'is_token_expired')
    search_fields = ('user__username',)
    readonly_fields = ('user', 'token', 'created_at')
    ordering = ('-created_at',)
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return True
    @admin.display(description='Expirado?', boolean=True)
    def is_token_expired(self, obj): return obj.is_expired()