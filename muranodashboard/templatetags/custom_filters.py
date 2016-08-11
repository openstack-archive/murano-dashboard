#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from django import forms
from django import template
from django.template import defaultfilters
from six.moves.urllib import parse as urlparse

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
    return urlparse.unquote(value)
