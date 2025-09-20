# questoes/templatetags/questoes_extras.py (VERSÃO CORRIGIDA E FINAL)

from django import template
from django.http import QueryDict
from gestao.forms import ExclusaoUsuarioForm

register = template.Library()

@register.filter
def remove_page_param(query_string):
    """
    Remove o parâmetro 'page' de uma querystring para uso na paginação.
    """
    query_dict = QueryDict(query_string).copy()
    if 'page' in query_dict:
        del query_dict['page']
    return query_dict.urlencode()

@register.simple_tag
def get_exclusao_form():
    """
    Retorna uma instância do formulário unificado de exclusão de usuário
    para ser usado em modais dentro dos templates.
    """
    return ExclusaoUsuarioForm()

# Nota: As importações de markdown e outros filtros foram removidas
# se não estiverem sendo usadas. Mantenha o arquivo o mais limpo possível.





