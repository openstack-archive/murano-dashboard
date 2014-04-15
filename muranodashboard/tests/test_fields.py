#    Copyright (c) 2013 Mirantis, Inc.
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

import unittest2 as unittest

from mock import patch

from muranodashboard.common import utils

from muranodashboard.dynamic_ui.fields import PostgreSqlChoiceField


class CustomFieldsTests(unittest.TestCase):
    def test_postgresql_choice_field_values(self):

        with patch('muranodashboard.dynamic_ui.fields.api') as mock:
            mock.service_list_by_type.return_value = [
                utils.Bunch(id='id1', name='examplePostgreSQL')]

            field = PostgreSqlChoiceField()
            field.update({'environment_id': None}, request='request')

            choices = dict(field.choices)

            self.assertIn('id1', choices)
            self.assertEqual(choices['id1'], 'examplePostgreSQL')
