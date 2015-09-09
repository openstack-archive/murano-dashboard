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
import testtools

from django import forms
from muranodashboard.dynamic_ui import services


class TestService(testtools.TestCase):
    def setUp(self):
        super(TestService, self).setUp()

        self.application = {'?': {'type': 'test.App'}}

    def test_service_field_hidden_false(self):
        """Test that service field is hidden

        When Service class instantiated with some field having `hidden`
        attribute set to `false` - the generated form field should have
        widget different from `HiddenInput`.

        Bug: #1368120
        """
        ui = [{
            'appConfiguration': {'fields': [{'hidden': False, 'type': 'string',
                                             'name': 'title'}]}
        }]

        service = services.Service(cleaned_data={},
                                   version=2,
                                   fqn='io.murano.Test',
                                   application=self.application,
                                   forms=ui)
        form = next(e for e in service.forms
                    if e.__name__ == 'appConfiguration')
        field = form.base_fields['title']

        self.assertNotIsInstance(field.widget, forms.HiddenInput)

    def test_service_field_hidden_true(self):
        """Test hidden widget

        `hidden: true` in UI definition results to HiddenInput in Django form.
        """
        ui = [{
            'appConfiguration': {'fields': [{'hidden': True, 'type': 'string',
                                             'name': 'title'}]}
        }]

        service = services.Service(cleaned_data={},
                                   version=2,
                                   fqn='io.murano.Test',
                                   application=self.application,
                                   forms=ui)
        form = next(e for e in service.forms
                    if e.__name__ == 'appConfiguration')
        field = form.base_fields['title']

        self.assertIsInstance(field.widget, forms.HiddenInput)
