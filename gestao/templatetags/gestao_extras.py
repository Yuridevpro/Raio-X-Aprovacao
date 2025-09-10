# gestao/templatetags/gestao_extras.py

from django import template
from django.contrib.auth.models import User

register = template.Library()

@register.simple_tag
def get_superuser_count():
    """Retorna a contagem de superusuários ativos no sistema."""
    return User.objects.filter(is_superuser=True, is_active=True).count()

# =======================================================================
# INÍCIO DA ADIÇÃO: Novo filtro 'split'
# =======================================================================
@register.filter
def split(value, key):
    """
    Filtro de template que divide uma string por um delimitador.
    Uso: {{ "maçã,banana,laranja"|split:"," }}
    """
    return value.split(key)
# =======================================================================
# FIM DA ADIÇÃO
# =======================================================================

# gestao/templatetags/gestao_extras.py

from django import template

@register.filter
def get_item(dictionary, key):
    """
    Permite acessar o valor de um dicionário usando uma variável como chave no template.
    Uso: {{ meu_dicionario|get_item:minha_variavel }}
    """
    return dictionary.get(key)

@register.simple_tag(takes_context=True)
def update_query_params(context, **kwargs):
    """
    Atualiza ou adiciona parâmetros a uma URL de query string.
    Ex: {% update_query_params sort_by='recent' page=1 %}
    """
    query_params = context['request'].GET.copy()
    for key, value in kwargs.items():
        query_params[key] = value
    return query_params.urlencode()

