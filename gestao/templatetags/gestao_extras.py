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