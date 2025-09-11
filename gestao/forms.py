# gestao/forms.py

from django import forms
from django.contrib.auth.models import User
# from django.db import models <-- CORREÇÃO: Removido import desnecessário. 'Choices' em forms.Form não usam models.
from .models import SolicitacaoExclusao

# =======================================================================
# FORMULÁRIO PARA GERENCIAR STATUS DE STAFF (Sem alterações)
# =======================================================================
class StaffUserForm(forms.ModelForm):
    """
    Formulário para superusuários editarem o status de staff de outros usuários.
    """
    class Meta:
        model = User
        fields = ['username', 'email', 'is_staff']
        widgets = {
            'is_staff': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }
        help_texts = {
            'is_staff': "Marque esta opção para conceder acesso ao painel de gestão a este usuário."
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].disabled = True
        self.fields['email'].disabled = True

# =======================================================================
# INÍCIO DO BLOCO CORRIGIDO: O Formulário de Exclusão Unificado
# =======================================================================
class ExclusaoUsuarioForm(forms.Form):
    """
    Formulário unificado para capturar o motivo da exclusão de um usuário.
    Usado tanto para exclusão direta (superuser) quanto para sugestão (staff).
    """
    # <-- CORREÇÃO: Em forms.Form, a prática padrão é definir 'choices' como uma lista de tuplas, não usando models.TextChoices.
    MOTIVO_CHOICES = [
        ('', '---------'), # Adicionado para ter uma opção vazia
        ('TERMOS_DE_SERVICO', 'Violação dos Termos de Serviço'),
        ('CONDUTA_INADEQUADA', 'Conduta Inadequada / Abusiva'),
        ('INATIVIDADE', 'Conta Inativa por Longo Período'),
        ('SEGURANCA', 'Atividade Suspeita / Risco de Segurança'),
        ('SOLICITACAO_USUARIO', 'A Pedido do Próprio Usuário'),
        ('OUTRO', 'Outro (detalhar abaixo)'),
    ]

    motivo_predefinido = forms.ChoiceField(
        choices=MOTIVO_CHOICES, # <-- CORREÇÃO: Usando a lista de tuplas definida acima.
        label="Selecione o motivo principal",
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=True
    )
    
    justificativa = forms.CharField(
        label="Justificativa Detalhada",
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'form-control',
            'placeholder': 'Forneça detalhes específicos sobre o motivo da exclusão.'
        }),
        required=False # A obrigatoriedade será controlada na view
    )