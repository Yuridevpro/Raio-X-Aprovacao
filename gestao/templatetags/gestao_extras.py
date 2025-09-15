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

@register.filter
def get_status_badge_class(status_value):
    """ Retorna a classe CSS para o badge de status do simulado. """
    if status_value == 'ATIVO':
        return 'bg-status-ativo'
    elif status_value == 'EM_BREVE':
        return 'bg-status-em-breve'
    elif status_value == 'ARQUIVADO':
        return 'bg-status-arquivado'
    return 'bg-secondary'

# =======================================================================
# INÍCIO DAS ADIÇÕES
# Filtros necessários para exibir os badges de disciplina nos cards de simulado.
# =======================================================================

@register.filter
def map_attribute(queryset, attribute_name):
    """
    Mapeia um queryset ou lista de objetos para uma lista de um atributo específico.
    Uso: {{ simulado.questoes.all|map_attribute:'disciplina' }}
    """
    # Garante que a função não falhe se o queryset for None
    if not queryset:
        return []
    return [getattr(obj, attribute_name) for obj in queryset if hasattr(obj, attribute_name)]

@register.filter
def unique_by_attribute(objects, attribute_name):
    """
    Filtra uma lista de objetos, mantendo apenas aqueles com um valor de atributo único.
    Essencial para obter uma lista de disciplinas sem repetição.
    Uso: {{ lista_de_disciplinas|unique_by_attribute:'id' }}
    """
    seen = set()
    result = []
    # Garante que a função não falhe se a lista de objetos for None
    if not objects:
        return []
    for obj in objects:
        if obj is None: 
            continue
        key = getattr(obj, attribute_name, None)
        # Adiciona à lista apenas se o objeto e sua chave não forem nulos e não tiverem sido vistos antes
        if key is not None and key not in seen:
            seen.add(key)
            result.append(obj)
    return result

# =======================================================================
# FIM DAS ADIÇÕES
# =======================================================================