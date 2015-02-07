from django import forms
from django import template
from django.template import defaultfilters
import urllib

register = template.Library()


@register.filter(name='is_checkbox')
def is_checkbox(field):
    return isinstance(field.field.widget, forms.CheckboxInput)


@register.filter(name='firsthalf')
def first_half(seq):
    half_len = len(seq) / 2
    return seq[:half_len]


@register.filter(name='lasthalf')
def last_half(seq):
    half_len = len(seq) / 2
    return seq[half_len:]


@register.filter(name='unquote')
@defaultfilters.stringfilter
def unquote_raw(value):
    return urllib.unquote(value)
