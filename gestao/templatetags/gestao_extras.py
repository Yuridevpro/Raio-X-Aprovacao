# gestao/templatetags/gestao_extras.py

from django import template
from django.contrib.auth.models import User
from ..forms import ExclusaoUsuarioForm  # Importante para o modal de exclusão

register = template.Library()

# =======================================================================
# SIMPLE TAGS
# Funções que podem ser chamadas diretamente no template.
# =======================================================================

@register.simple_tag
def get_superuser_count():
    """
    Retorna a contagem de superusuários ativos no sistema.
    Uso: {% get_superuser_count as var_name %}
    """
    return User.objects.filter(is_superuser=True, is_active=True).count()

@register.simple_tag
def get_exclusao_form():
    """
    Retorna uma instância do formulário de motivo de exclusão.
    Essencial para os modais de exclusão de usuário.
    Uso: {% get_exclusao_form as form %}
    """
    return ExclusaoUsuarioForm()

@register.simple_tag(takes_context=True)
def update_query_params(context, **kwargs):
    """
    Atualiza ou adiciona parâmetros a uma URL de query string,
    preservando os parâmetros existentes. Útil para paginação, filtros e ordenação.
    Uso: <a href="?{% update_query_params page=1 sort_by='recent' %}">Link</a>
    """
    # Cria uma cópia mutável dos parâmetros GET da requisição atual
    query_params = context['request'].GET.copy()
    
    # Itera sobre os argumentos passados para a tag
    for key, value in kwargs.items():
        # Adiciona ou atualiza o valor do parâmetro
        query_params[key] = value
        
    # Retorna a string de query codificada para ser usada na URL
    return query_params.urlencode()


# =======================================================================
# FILTERS
# Funções que modificam variáveis diretamente no template.
# =======================================================================

@register.filter(name='split')
def split_string(value, key):
    """
    Filtro de template que divide uma string por um delimitador.
    Uso: {{ "maçã,banana,laranja"|split:"," }}
    """
    return value.split(key)

@register.filter
def get_item(dictionary, key):
    """
    Permite acessar o valor de um dicionário usando uma variável como chave.
    Útil quando a chave do dicionário não é uma string literal.
    Uso: {{ meu_dicionario|get_item:minha_variavel_de_chave }}
    """
    return dictionary.get(key)