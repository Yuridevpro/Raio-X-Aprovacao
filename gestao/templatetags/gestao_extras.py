# gestao/templatetags/gestao_extras.py

from django import template
from django.contrib.auth.models import User
from ..forms import ExclusaoUsuarioForm

register = template.Library()

@register.simple_tag
def get_superuser_count():
    return User.objects.filter(is_superuser=True, is_active=True).count()

@register.simple_tag
def get_exclusao_form():
    return ExclusaoUsuarioForm()

@register.simple_tag(takes_context=True)
def update_query_params(context, **kwargs):
    query_params = context['request'].GET.copy()
    for key, value in kwargs.items():
        query_params[key] = value
    return query_params.urlencode()

@register.filter(name='split')
def split_string(value, key):
    return value.split(key)

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def get_status_badge_class(status_value):
    if status_value == 'ATIVO':
        return 'bg-status-ativo'
    elif status_value == 'EM_BREVE':
        return 'bg-status-em-breve'
    elif status_value == 'ARQUIVADO':
        return 'bg-status-arquivado'
    return 'bg-secondary'

@register.filter
def status_to_color(status):
    color_map = { 'ATIVO': '#198754', 'EM_BREVE': '#ffc107', 'ARQUIVADO': '#6c757d' }
    return color_map.get(status, '#6c757d')

@register.filter
def status_to_bg_class(status):
    class_map = { 'ATIVO': 'bg-success', 'EM_BREVE': 'bg-warning text-dark', 'ARQUIVADO': 'bg-secondary' }
    return class_map.get(status, 'bg-secondary')

@register.filter
def dificuldade_to_bg_class(dificuldade):
    """Retorna classes CSS para o badge de dificuldade."""
    class_map = {
        'FACIL': 'bg-success-soft text-success',
        'MEDIO': 'bg-warning-soft text-warning',
        'DIFICIL': 'bg-danger-soft text-danger',
    }
    return class_map.get(dificuldade, 'bg-secondary-soft text-secondary')

@register.filter
def map_attribute(queryset, attribute_name):
    if not queryset:
        return []
    return [getattr(obj, attribute_name) for obj in queryset if hasattr(obj, attribute_name)]

@register.filter
def unique_by_attribute(objects, attribute_name):
    seen = set()
    result = []
    if not objects:
        return []
    for obj in objects:
        if obj is None: 
            continue
        key = getattr(obj, attribute_name, None)
        if key is not None and key not in seen:
            seen.add(key)
            result.append(obj)
    return result