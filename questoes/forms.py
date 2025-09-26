# questoes/forms.py

from django import forms
from .models import Questao, Disciplina, Assunto 
import json
from django.contrib.auth.models import User
import bleach # ✅ ADICIONE ESTA IMPORTAÇÃO
import html



# =======================================================================
# FORMULÁRIO BASE PARA QUESTÕES (COM A CORREÇÃO DEFINITIVA)
# =======================================================================
# questoes/forms.py

from django import forms
from .models import Questao, Disciplina, Assunto 
import json
from django.contrib.auth.models import User
import bleach # ✅ ADICIONADO

# questoes/forms.py

from django import forms
from .models import Questao, Disciplina, Assunto 
import json
from django.contrib.auth.models import User

# As importações de bleach e html não são mais necessárias aqui

class BaseQuestaoForm(forms.ModelForm):
    """
    Formulário base com a lógica principal para criar e editar uma questão,
    incluindo os campos de alternativa virtuais e a estilização padrão do Bootstrap.
    """
    alternativa_a = forms.CharField(label="Alternativa A", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=True)
    alternativa_b = forms.CharField(label="Alternativa B", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=True)
    alternativa_c = forms.CharField(label="Alternativa C", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=True)
    alternativa_d = forms.CharField(label="Alternativa D", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=True)
    alternativa_e = forms.CharField(label="Alternativa E", widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}), required=False)

    class Meta:
        model = Questao
        fields = (
            'disciplina', 'assunto', 'banca', 'instituicao', 'ano', 
            'imagem_enunciado', 'enunciado', 'gabarito', 'explicacao', 'is_inedita'
        )
        # =======================================================================
        # ✅ INÍCIO DA CORREÇÃO: Voltando para Textarea padrão
        # =======================================================================
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
        # =======================================================================
        # FIM DA CORREÇÃO
        # =======================================================================

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.alternativas:
            alternativas_dict = self.instance.get_alternativas_dict()
            self.fields['alternativa_a'].initial = alternativas_dict.get('A', '')
            self.fields['alternativa_b'].initial = alternativas_dict.get('B', '')
            self.fields['alternativa_c'].initial = alternativas_dict.get('C', '')
            self.fields['alternativa_d'].initial = alternativas_dict.get('D', '')
            self.fields['alternativa_e'].initial = alternativas_dict.get('E', '')

    def clean(self):
        cleaned_data = super().clean()
        gabarito = cleaned_data.get("gabarito")
        alternativa_e = cleaned_data.get("alternativa_e")

        if gabarito == 'E' and not alternativa_e:
            self.add_error('alternativa_e', 'Você não pode marcar o gabarito como "E" e deixar a alternativa "E" vazia.')
        
        return cleaned_data
            
    def save(self, commit=True):
        alternativas_dict = {
            'A': self.cleaned_data['alternativa_a'],
            'B': self.cleaned_data['alternativa_b'],
            'C': self.cleaned_data['alternativa_c'],
            'D': self.cleaned_data['alternativa_d'],
        }
        
        if self.cleaned_data.get('alternativa_e'):
            alternativas_dict['E'] = self.cleaned_data['alternativa_e']

        self.instance.alternativas = alternativas_dict
        
        # A lógica de clean_enunciado e clean_explicacao não é mais necessária.
        return super().save(commit)
    
    
class AdminQuestaoForm(BaseQuestaoForm):
    pass

class GestaoQuestaoForm(BaseQuestaoForm):
    class Meta(BaseQuestaoForm.Meta):
        widgets = {
            **BaseQuestaoForm.Meta.widgets,
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
            'is_inedita': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }

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

