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

@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Esta tag permite substituir ou adicionar parâmetros GET na URL atual.
    
    Uso no template: {% url_replace status='resolvidas' page=1 %}
    
    Ela pega todos os parâmetros da URL atual, atualiza com os que você passou
    e remove o parâmetro 'page' para sempre voltar à primeira página ao
    mudar um filtro.
    """
    # Pega uma cópia mutável dos parâmetros GET da requisição atual
    query = context['request'].GET.copy()
    
    # Itera sobre os argumentos passados para a tag (ex: status='resolvidas')
    for key, value in kwargs.items():
        # Se o valor for uma string não vazia, define o parâmetro
        if value is not None and value != '':
            query[key] = value
        # Se o valor for vazio ou None, remove o parâmetro da URL
        elif key in query:
            del query[key]
            
    # Sempre remove o parâmetro 'page' para resetar a paginação ao aplicar filtros
    if 'page' in query:
        del query['page']
        
    # Retorna a string de query final, pronta para ser usada no href
    return query.urlencode()