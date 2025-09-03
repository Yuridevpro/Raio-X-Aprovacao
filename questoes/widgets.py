from django import forms
from django.forms.widgets import Textarea

class TiptapEditorWidget(Textarea):
    # O caminho para o template HTML que irá renderizar o nosso editor.
    template_name = 'questoes/widgets/tiptap_widget.html'

    # A classe Media é a forma como o Django anexa arquivos JS e CSS
    # # a um widget quando ele é renderizado na página.
    # class Media:
    #     # CSS para estilizar o editor, similar ao do seu frontend.
    #     css = {
    #         'all': ('questoes/css/tiptap_admin.css',)
    #     }
    #     # JS necessário para o Tiptap funcionar.
    #     js = (
    #         # 1. O script que exporta os módulos do Tiptap para o window object.
    #         'questoes/js/tiptap_loader.js',
    #         # 2. O script que de fato inicializa o editor.
    #         # O 'defer' garante que ele só execute após o loader.
    #         'questoes/js/tiptap_admin_init.js',
    #     )