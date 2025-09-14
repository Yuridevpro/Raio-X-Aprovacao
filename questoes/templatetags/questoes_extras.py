# questoes/templatetags/questoes_extras.py (ARQUIVO CORRIGIDO)

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
import markdown
from django.http import QueryDict

# =======================================================================
# INÍCIO DA CORREÇÃO: O form está em 'gestao.forms', não em 'gestao.models'
# =======================================================================
from gestao.forms import ExclusaoUsuarioForm
# =======================================================================
# FIM DA CORREÇÃO
# =======================================================================

register = template.Library()

@register.filter
def remove_page_param(query_string):
    query_dict = QueryDict(query_string).copy()
    if 'page' in query_dict:
        del query_dict['page']
    return query_dict.urlencode()

@register.simple_tag
def get_exclusao_form():
    """
    Retorna uma instância do formulário unificado de exclusão de usuário.
    """
    return ExclusaoUsuarioForm()