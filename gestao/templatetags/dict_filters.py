from django import template

register = template.Library()

@register.filter(name='get_item')
def get_item(obj, key):
    if isinstance(obj, dict):
        return obj.get(key)
    elif isinstance(obj, (list, tuple)):
        try:
            return obj[int(key)]
        except (IndexError, ValueError, TypeError):
            return None
    return None
