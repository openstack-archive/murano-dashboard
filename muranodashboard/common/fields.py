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

from muranodashboard.common import widgets

from django.core.exceptions import ValidationError
from django.core import validators
from django import forms
from django.utils.translation import ugettext_lazy as _


class TriStateMultipleChoiceField(forms.ChoiceField):
    """A multiple choice checkbox field where checkboxes has three states.

    States are:

        - Checked
        - Unchecked
        - Indeterminate

    It takes a ``dict`` instance as a value,
    where keys are internal values from `choices`
    and values are ones from following (in order respectively to states):

        - True
        - False
        - None
    """
    widget = widgets.TriStateCheckboxSelectMultiple
    default_error_messages = {
        'invalid_choice': _('Select a valid choice. %(value)s is not one '
                            'of the available choices.'),
        'invalid_value': _('Enter a dict with choices and values. '
                           'Got %(value)s.'),
    }

    def to_python(self, value):
        """Checks if value, that comes from widget, is a dict."""
        if value in validators.EMPTY_VALUES:
            return {}
        elif not isinstance(value, dict):
            raise ValidationError(self.error_messages['invalid_value'],
                                  code='invalid_value')
        return value

    def validate(self, value):
        """Ensures that value has only allowed values."""
        if not set(value.keys()) <= {k for k, _ in self.choices}:
            raise ValidationError(
                self.error_messages['invalid_choice'],
                code='invalid_choice',
                params={'value': value},
            )
        elif not (set(value.values()) <=
                  set(widgets.TriStateCheckboxSelectMultiple
                      .VALUES_MAP.values())):
            raise ValidationError(
                self.error_messages['invalid_value'],
                code='invalid_value',
                params={'value': value},
            )
