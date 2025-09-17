# simulados/forms.py

from django import forms
from questoes.models import Disciplina

class SimuladoAvancadoForm(forms.Form):
    """
    Formulário para a validação inicial da criação avançada de simulado.
    Os campos dinâmicos de disciplina/quantidade são validados na view.
    """
    nome = forms.CharField(
        label="Nome do Simulado", 
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg', 'placeholder': 'Ex: Revisão Semanal de Constitucional'})
    )
    tempo_por_questao = forms.IntegerField(
        label="Minutos por questão",
        required=False, # 0 ou nulo será tratado como ilimitado
    )