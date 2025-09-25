# usuarios/templatetags/colecao_extras.py
from django import template


register = template.Library()

@register.simple_tag
def rarity_class(rarity_value):
    """Retorna uma classe CSS com base no valor da raridade para o badge."""
    return f"rarity-{rarity_value.lower()}"

@register.filter(name='class_name')
def class_name(value):
    """Retorna o nome da classe de um objeto de forma segura."""
    return value.__class__.__name__