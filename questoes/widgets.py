# questoes/widgets.py

from django import forms

class TiptapEditorWidget(forms.Textarea):
    """
    Widget customizado que renderiza um editor Tiptap.
    Ele substitui um <textarea> padrão pelo HTML completo do editor.
    """
    # Aponta para o template que criamos no Passo 1
    template_name = 'questoes/widgets/tiptap_widget.html'

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        # Passa o atributo 'placeholder' para o template do widget
        context['widget']['attrs']['placeholder'] = self.attrs.get('placeholder', '')
        return context