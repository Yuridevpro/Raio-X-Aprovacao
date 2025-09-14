# simulados/templatetags/markdown_extras.py

import markdown
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='markdownify')
def markdownify(text):
    """
    Converte um texto em Markdown para HTML, usando extensões comuns.
    O mark_safe é crucial para que o Django não escape o HTML gerado.
    """
    return mark_safe(markdown.markdown(text, extensions=['fenced_code', 'tables']))