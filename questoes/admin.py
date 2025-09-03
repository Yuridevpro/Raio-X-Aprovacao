# questoes/admin.py

from django.contrib import admin
from django import forms
from .models import Disciplina, Banca, Assunto, Questao, Instituicao # Importado 'Instituicao'
import json
from easymde.widgets import EasyMDEEditor

# Registra os modelos
admin.site.register(Disciplina)
admin.site.register(Banca)
admin.site.register(Assunto)
admin.site.register(Instituicao) # Registrado o novo modelo 'Instituicao'

class QuestaoAdminForm(forms.ModelForm):
    # Campos virtuais para as alternativas
    alternativa_a = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'cols': 80}), required=True)
    alternativa_b = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'cols': 80}), required=True)
    alternativa_c = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'cols': 80}), required=True)
    alternativa_d = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'cols': 80}), required=True)
    alternativa_e = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'cols': 80}), required=True)

    class Meta:
        model = Questao
        # --- CAMPO 'instituicao' ADICIONADO À LISTA DE CAMPOS ---
        fields = ('disciplina', 'assunto', 'banca', 'instituicao', 'ano', 'imagem_enunciado', 'enunciado', 'gabarito', 'explicacao', 'is_inedita')
        
        widgets = {
            'enunciado': EasyMDEEditor(),
            'explicacao': EasyMDEEditor(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
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
        self.instance.alternativas = json.dumps(alternativas_dict)
        return super().save(commit)

@admin.register(Questao)
class QuestaoAdmin(admin.ModelAdmin):
    form = QuestaoAdminForm
    
    # --- 'instituicao' ADICIONADO AO LIST_DISPLAY E LIST_FILTER ---
    list_display = ('id', 'disciplina', 'assunto', 'banca', 'instituicao', 'ano', 'is_inedita')
    list_filter = ('disciplina', 'banca', 'instituicao', 'ano', 'is_inedita')
    
    search_fields = ('enunciado', 'explicacao')
    list_editable = ('is_inedita',)
    ordering = ('-id',)

    class Media:
        js = ('admin/js/questao_admin.js',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.criada_por = request.user
        super().save_model(request, obj, form, change)