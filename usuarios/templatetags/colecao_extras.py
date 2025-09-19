# usuarios/templatetags/colecao_extras.py

from django import template

register = template.Library()

@register.simple_tag
def rarity_class(rarity_value):
    """Retorna uma classe CSS com base no valor da raridade."""
    return f"rarity-{rarity_value.lower()}"