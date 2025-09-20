# gamificacao/templatetags/gamificacao_extras.py (NOVO ARQUIVO)

from django import template

register = template.Library()

@register.filter(name='class_name')
def class_name(value):
    """Retorna o nome da classe de um objeto."""
    return value.__class__.__name__

@register.filter(name='get_item')
def get_item(dictionary, key):
    """
    Permite acessar um valor de um dicionário usando uma variável como chave no template.
    Uso: {{ meu_dicionario|get_item:minha_chave }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None