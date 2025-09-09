# questoes/templatetags/questoes_extras.py

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
import markdown
from django.http import QueryDict

# =======================================================================
# INÍCIO DA MUDANÇA: Importar apenas o novo formulário unificado
# =======================================================================
from gestao.forms import ExclusaoUsuarioForm
# =======================================================================
# FIM DA MUDANÇA
# =======================================================================


register = template.Library()


@register.filter
def remove_page_param(query_string):
    """
    Remove o parâmetro 'page' de uma query string, útil para a paginação.
    """
    query_dict = QueryDict(query_string).copy()
    if 'page' in query_dict:
        del query_dict['page']
    return query_dict.urlencode()


# =======================================================================
# INÍCIO DA MUDANÇA: Substituir as tags antigas por uma única tag nova
# =======================================================================
@register.simple_tag
def get_exclusao_form():
    """
    Retorna uma instância do formulário unificado de exclusão de usuário.
    Esta tag será usada tanto pelo modal de exclusão direta (superuser)
    quanto pelo modal de sugestão (staff).
    """
    return ExclusaoUsuarioForm()
# =======================================================================
# FIM DA MUDANÇA
# =======================================================================

