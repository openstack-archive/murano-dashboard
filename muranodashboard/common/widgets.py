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

import floppyforms as floppy


class TriStateCheckboxSelectMultiple(floppy.widgets.Input):
    """Renders tri-state multi-selectable checkbox.

    .. note:: Subclassed from ``CheckboxSelectMultiple`` and not from
       ``SelectMultiple`` only to make
       ``horizon.templatetags.form_helpers.is_checkbox`` able to recognize
       this widget.

       Otherwise template ``horizon/common/_form_field.html`` would render
       this widget slightly incorrectly.
    """
    template_name = 'common/tri_state_checkbox/base.html'

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
