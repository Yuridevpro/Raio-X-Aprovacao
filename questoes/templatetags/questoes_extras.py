# pratica/templatetags/

from django import template
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
import markdown
from django.http import QueryDict

register = template.Library()



@register.filter
def remove_page_param(query_string):
    query_dict = QueryDict(query_string).copy()
    if 'page' in query_dict:
        del query_dict['page']
    return query_dict.urlencode()