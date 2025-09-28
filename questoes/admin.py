# questoes/admin.py
from django.contrib import admin
from .models import Disciplina, Banca, Assunto, Questao, Instituicao
from .forms import BaseQuestaoForm 
from .widgets import TiptapEditorWidget

# Registra os modelos simples usando o admin.site padrão
admin.site.register(Disciplina)
admin.site.register(Banca)
admin.site.register(Assunto)
admin.site.register(Instituicao)

@admin.register(Questao)
class QuestaoAdmin(admin.ModelAdmin):
    form = BaseQuestaoForm
    
    list_display = ('id', 'codigo', 'disciplina', 'assunto', 'banca', 'instituicao', 'ano', 'is_inedita')
    list_filter = ('disciplina', 'banca', 'instituicao', 'ano', 'is_inedita')
    search_fields = ('codigo', 'enunciado', 'explicacao')
    list_editable = ('is_inedita',)
    ordering = ('-id',)
    raw_id_fields = ('disciplina', 'assunto', 'banca', 'instituicao', 'criada_por', 'deleted_by')

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        form.base_fields['enunciado'].widget = TiptapEditorWidget()
        form.base_fields['explicacao'].widget = TiptapEditorWidget()
        form.base_fields['enunciado'].widget.attrs.clear()
        form.base_fields['explicacao'].widget.attrs.clear()
        
        return form

    class Media:
        js = ('admin/js/questao_admin.js',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.criada_por = request.user
        super().save_model(request, obj, form, change)