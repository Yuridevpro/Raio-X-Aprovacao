# pratica/templatetags/pratica_extras.py

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
import markdown

register = template.Library()

@register.filter(name='render_markdown')
@stringfilter
def render_markdown(value):
    """
    Converte uma string de Markdown para HTML seguro.
    Este filtro é usado na área de prática para renderizar enunciados de questões
    e o conteúdo dos comentários dos usuários.
    """
    # Adicionar extensões pode ser útil para GFM (GitHub Flavored Markdown), tabelas, etc.
    # Ex: extensions=['fenced_code', 'tables']
    return mark_safe(markdown.markdown(value))

    return query_dict.urlencode()