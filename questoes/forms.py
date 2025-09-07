# questoes/forms.py

from django import forms
from .models import Questao, Disciplina, Assunto 
import json

# =======================================================================
# FORMULÁRIO BASE PARA QUESTÕES (SEM ALTERAÇÕES)
# =======================================================================
class BaseQuestaoForm(forms.ModelForm):
    """
    Formulário base com a lógica principal para criar e editar uma questão,
    incluindo os campos de alternativa virtuais e a estilização padrão do Bootstrap.
    """
    alternativa_a = forms.CharField(label="Alternativa A", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=True)
    alternativa_b = forms.CharField(label="Alternativa B", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=True)
    alternativa_c = forms.CharField(label="Alternativa C", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=True)
    alternativa_d = forms.CharField(label="Alternativa D", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=True)
    alternativa_e = forms.CharField(label="Alternativa E", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=True)

    class Meta:
        model = Questao
        fields = (
            'disciplina', 'assunto', 'banca', 'instituicao', 'ano', 
            'imagem_enunciado', 'enunciado', 'gabarito', 'explicacao', 'is_inedita'
        )
        widgets = {
            'disciplina': forms.Select(attrs={'class': 'form-select'}),
            'assunto': forms.Select(attrs={'class': 'form-select'}),
            'banca': forms.Select(attrs={'class': 'form-select'}),
            'instituicao': forms.Select(attrs={'class': 'form-select'}),
            'ano': forms.NumberInput(attrs={'class': 'form-control'}),
            'imagem_enunciado': forms.FileInput(attrs={'class': 'form-control'}),
            'enunciado': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
            'gabarito': forms.Select(attrs={'class': 'form-select'}),
            'explicacao': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
            'is_inedita': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.alternativas:
            alternativas_dict = self.instance.get_alternativas_dict()
            self.fields['alternativa_a'].initial = alternativas_dict.get('A', '')
            self.fields['alternativa_b'].initial = alternativas_dict.get('B', '')
            self.fields['alternativa_c'].initial = alternativas_dict.get('C', '')
            self.fields['alternativa_d'].initial = alternativas_dict.get('D', '')
            self.fields['alternativa_e'].initial = alternativas_dict.get('E', '')
            
    def save(self, commit=True):
        alternativas_dict = {
            'A': self.cleaned_data['alternativa_a'],
            'B': self.cleaned_data['alternativa_b'],
            'C': self.cleaned_data['alternativa_c'],
            'D': self.cleaned_data['alternativa_d'],
            'E': self.cleaned_data['alternativa_e'],
        }
        self.instance.alternativas = json.dumps(alternativas_dict, ensure_ascii=False)
        return super().save(commit)

# =======================================================================
# MODIFICAÇÃO 1: Renomeado para AdminQuestaoForm.
# Este formulário será usado pelo Django Admin e pode ter o widget Tiptap.
# =======================================================================
class AdminQuestaoForm(BaseQuestaoForm):
    pass

# =======================================================================
# MODIFICAÇÃO 2: Criado o GestaoQuestaoForm para o frontend.
# Ele herda do BaseQuestaoForm mas sobrescreve os widgets para usar
# textareas simples com placeholders e classes corretas.
# =======================================================================
class GestaoQuestaoForm(BaseQuestaoForm):
    class Meta(BaseQuestaoForm.Meta):
        widgets = {
            **BaseQuestaoForm.Meta.widgets, # Herda todos os widgets da classe base
            'enunciado': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 8, 
                'placeholder': 'Digite o enunciado da questão aqui. Você pode usar Markdown para formatação.'
            }),
            'explicacao': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 5, 
                'placeholder': 'Digite a explicação detalhada do gabarito. Este campo é opcional, mas altamente recomendado.'
            }),
            # Aproveitamos para melhorar o widget do campo 'is_inedita' para o novo design
            'is_inedita': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

# =======================================================================
# INÍCIO: NOVOS FORMULÁRIOS PARA O PAINEL DE GESTÃO (SEM ALTERAÇÕES)
# =======================================================================
class EntidadeSimplesForm(forms.Form):
    nome = forms.CharField(label="Nome", max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))

class AssuntoForm(forms.Form):
    disciplina = forms.ModelChoiceField(
        queryset=Disciplina.objects.all().order_by('nome'),
        label="Selecione a Disciplina",
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    nome = forms.CharField(
        label="Nome do Novo Assunto",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
