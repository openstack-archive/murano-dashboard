from django import template


register = template.Library()


@register.filter(name='is_checkbox')
def is_checkbox(field):
    return field.field.widget.__class__.__name__ == 'CheckboxInput'
