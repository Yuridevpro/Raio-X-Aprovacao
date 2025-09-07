# questoes/widgets.py

from django import forms

# A classe base foi alterada de 'Textarea' para 'forms.Widget'
class TiptapEditorWidget(forms.Widget):
    # O caminho para o template HTML que irá renderizar o nosso editor.
    template_name = 'questoes/widgets/tiptap_widget.html'

    # Adicionar este método é uma boa prática para garantir que o valor
    # do campo seja passado corretamente para o contexto do template.
    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # O template (tiptap_widget.html) espera o valor em 'widget.value'
        context['widget']['value'] = value or ''
        return context