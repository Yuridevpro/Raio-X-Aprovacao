# questoes/admin.py

from django.contrib import admin
from .models import Disciplina, Banca, Assunto, Questao, Instituicao
# --- INÍCIO DAS MUDANÇAS ---
# Importamos o formulário BASE (sem Tiptap) e o widget Tiptap separadamente
from .forms import BaseQuestaoForm 
from .widgets import TiptapEditorWidget
# --- FIM DAS MUDANÇAS ---

# Registra os modelos simples
admin.site.register(Disciplina)
admin.site.register(Banca)
admin.site.register(Assunto)
admin.site.register(Instituicao)

@admin.register(Questao)
class QuestaoAdmin(admin.ModelAdmin):
    # --- ALTERADO ---
    # O admin agora usa o BaseQuestaoForm, que tem a lógica mas não o widget Tiptap por padrão.
    form = BaseQuestaoForm
    
    list_display = ('id', 'codigo', 'disciplina', 'assunto', 'banca', 'instituicao', 'ano', 'is_inedita')
    list_filter = ('disciplina', 'banca', 'instituicao', 'ano', 'is_inedita')
    search_fields = ('codigo', 'enunciado', 'explicacao')
    list_editable = ('is_inedita',)
    ordering = ('-id',)

    # --- ALTERADO ---
 # --- INÍCIO DA ALTERAÇÃO ---
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        
        # Define o widget Tiptap para os campos desejados
        form.base_fields['enunciado'].widget = TiptapEditorWidget()
        form.base_fields['explicacao'].widget = TiptapEditorWidget()

        # Limpa os atributos para evitar conflitos de classe CSS (como 'form-control')
        # que podem fazer o textarea oculto aparecer.
        form.base_fields['enunciado'].widget.attrs.clear()
        form.base_fields['explicacao'].widget.attrs.clear()
        
        return form
    # --- FIM DA ALTERAÇÃO ---

    class Media:
        # Este JS é para a lógica de esconder 'Banca' e 'Ano' quando 'is_inedita' é marcado
        js = ('admin/js/questao_admin.js',)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.criada_por = request.user
        super().save_model(request, obj, form, change)