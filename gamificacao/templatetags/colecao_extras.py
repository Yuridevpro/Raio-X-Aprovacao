# gamificacao/templatetags/colecao_extras.py
from django import template

register = template.Library()

@register.filter(name='class_name')
def class_name(value):
    return value.__class__.__name__.lower()

@register.simple_tag
def rarity_class(raridade_string):
    """Retorna uma classe CSS com base na string de raridade."""
    if not raridade_string:
        return ""
    return f"rarity-{raridade_string.lower()}"