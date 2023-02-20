#    Copyright (c) 2015 Mirantis, Inc.
#
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

import itertools as it

from django import forms
from django.template import loader
from django.utils.encoding import force_str
from django.utils import formats

from muranodashboard.common import utils


# Widge and Input code is copied from https://github.com/gregmuellegger/
# django-floppyforms/blob/master/floppyforms/widgets.py to remove the
# dependency of django-floppyforms due to not very well supported anymore
# and was dropped from Ubuntu in Xenial.
class Widget(forms.Widget):
    is_required = False

    # Backported from Django 1.7
    @property
    def is_hidden(self):
        return self.input_type == 'hidden' \
            if hasattr(self, 'input_type') else False

    # Backported from Django 1.9
    if not hasattr(forms.Widget, 'format_value'):
        def format_value(self, value):
            return self._format_value(value)


class Input(Widget):
    template_name = 'common/tri_state_checkbox/base.html'
    input_type = None
    datalist = None

    def __init__(self, *args, **kwargs):
        datalist = kwargs.pop('datalist', None)
        if datalist is not None:
            self.datalist = datalist
        template_name = kwargs.pop('template_name', None)
        if template_name is not None:
            self.template_name = template_name
        super(Input, self).__init__(*args, **kwargs)
        # This attribute is used to inject a surrounding context in the
        # floppyforms templatetags, when rendered inside a complete form.
        self.context_instance = None

    def get_context_data(self):
        return {}

    def _format_value(self, value):
        if self.is_localized:
            value = formats.localize_input(value)
        return force_str(value)

    def get_context(self, name, value, attrs=None):
        context = {
            'type': self.input_type,
            'name': name,
            'hidden': self.is_hidden,
            'required': self.is_required,
            'True': True,
        }
        # True is injected in the context to allow stricter comparisons
        # for widget attrs. See #25.
        if self.is_hidden:
            context['hidden'] = True

        if value is None:
            value = ''

        if value != '':
            # Only add the value if it is non-empty
            context['value'] = self.format_value(value)

        context.update(self.get_context_data())
        context['attrs'] = self.build_attrs(attrs)

        for key, attr in context['attrs'].items():
            if attr == 1:
                # 1 == True so 'key="1"' will show up only as 'key'
                # Casting to a string so that it doesn't equal to True
                # See #25.
                if not isinstance(attr, bool):
                    context['attrs'][key] = str(attr)

        if self.datalist is not None:
            context['datalist'] = self.datalist
        return context

    def render(self, name, value, attrs=None, **kwargs):
        template_name = kwargs.pop('template_name', None)
        if template_name is None:
            template_name = self.template_name
        context = self.get_context(name, value, attrs=attrs or {})
        context = utils.flatten_contexts(self.context_instance, context)
        return loader.render_to_string(template_name, context)


class TriStateCheckboxSelectMultiple(Input):
    """Renders tri-state multi-selectable checkbox.

    .. note:: Subclassed from ``CheckboxSelectMultiple`` and not from
       ``SelectMultiple`` only to make
       ``horizon.templatetags.form_helpers.is_checkbox`` able to recognize
       this widget.

       Otherwise template ``horizon/common/_form_field.html`` would render
       this widget slightly incorrectly.
    """

    VALUES_MAP = {
        'True': True,
        'False': False,
        'None': None
    }

    def get_context(self, name, value, attrs=None, choices=()):
        """Renders html and JavaScript.

        :param value: Dictionary of form
                      Choice => Value (Checked|Uncheckec|Indeterminate)
        :type value: dict
        """
        context = super(TriStateCheckboxSelectMultiple, self).get_context(
            name, value, attrs
        )

        choices = dict(it.chain(self.choices, choices))
        if value is None:
            value = dict.fromkeys(choices, False)
        else:
            value = dict(dict.fromkeys(choices, False).items() +
                         value.items())

        context['values'] = [
            (choice, label, value[choice])
            for choice, label in choices.iteritems()
        ]

        return context

    @classmethod
    def parse_value(cls, value):
        """Converts encoded string with value to Python values."""
        choice, value = value.split('=')
        value = cls.VALUES_MAP[value]

        return choice, value

    def value_from_datadict(self, data, files, name):
        """Expects values in ``"key=False/True/None"`` form."""
        try:
            values = data.getlist(name)
        except AttributeError:
            if name in data:
                values = [data[name]]
            else:
                values = []

        return dict(map(self.parse_value, values))


class ExtraContextWidgetMixin(object):
    def __init__(self, *args, **kwargs):
        super(ExtraContextWidgetMixin, self).__init__(*args, **kwargs)

        self.extra_context = kwargs.pop('extra_context', {})

    def get_context(self, *args, **kwargs):
        context = super(ExtraContextWidgetMixin, self).get_context(
            *args, **kwargs
        )
        context.update(self.extra_context)
        return context
