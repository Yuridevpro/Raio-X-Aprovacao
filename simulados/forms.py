# simulados/forms.py (NOVO ARQUIVO)

from django import forms
from questoes.models import Disciplina

class QuestaoFiltroForm(forms.Form):
    """
    Formulário para o usuário selecionar filtros e gerar um simulado personalizado.
    """
    disciplina = forms.ModelChoiceField(
        queryset=Disciplina.objects.all().order_by('nome'),
        label="Disciplina",
        required=True,
        empty_label="Selecione uma disciplina",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    NUM_QUESTOES_CHOICES = [
        (10, '10 questões'),
        (20, '20 questões'),
        (30, '30 questões'),
        (50, '50 questões'),
    ]
    num_questoes = forms.ChoiceField(
        choices=NUM_QUESTOES_CHOICES,
        label="Número de Questões",
        required=True,
        initial=20,
        widget=forms.Select(attrs={'class': 'form-select'})
    )