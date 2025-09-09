# gestao/forms.py

from django import forms
from django.contrib.auth.models import User
from django.db import models # <-- MUDANÇA 1: Importar o módulo 'models'
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
# INÍCIO DO BLOCO NOVO: O Formulário de Exclusão Unificado e Inteligente
# =======================================================================
class ExclusaoUsuarioForm(forms.Form):
    # As opções de motivo agora são compartilhadas
    class MotivoExclusao(models.TextChoices):
        TERMOS_DE_SERVICO = 'TERMOS_DE_SERVICO', 'Violação dos Termos de Serviço'
        CONDUTA_INADEQUADA = 'CONDUTA_INADEQUADA', 'Conduta Inadequada / Abusiva'
        INATIVIDADE = 'INATIVIDADE', 'Conta Inativa por Longo Período'
        SEGURANCA = 'SEGURANCA', 'Atividade Suspeita / Risco de Segurança'
        SOLICITACAO_USUARIO = 'SOLICITACAO_USUARIO', 'A Pedido do Próprio Usuário'
        OUTRO = 'OUTRO', 'Outro (detalhar abaixo)'

    motivo_predefinido = forms.ChoiceField(
        choices=MotivoExclusao.choices,
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