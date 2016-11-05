#    Copyright (c) 2016 Mirantis, Inc.
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

from muranodashboard.dynamic_ui import helpers


class TestHelper(testtools.TestCase):
    def test_to_str(self):
        names = ['string', b'ascii', u'ascii',
                 u'\u043d\u0435 \u0430\u0441\u043a\u0438']
        for name in names:
            self.assertIsInstance(helpers.to_str(name), str)

    def test_int2base(self):
        for x in range(30):
            self.assertEqual("{0:b}".format(x), helpers.int2base(x, 2))
            self.assertEqual("{0:o}".format(x), helpers.int2base(x, 8))
            self.assertEqual("{0:x}".format(x), helpers.int2base(x, 16))

    def test_camelize(self):
        snake_name = "snake_case_name"
        camel_name = helpers.camelize(snake_name)
        self.assertEqual("SnakeCaseName", camel_name)

    def test_explode(self):
        not_string = 123456
        explode_int = helpers.explode(not_string)
        self.assertEqual(123456, explode_int)

        string = "test"
        explode_str = helpers.explode(string)
        self.assertEqual(['t', 'e', 's', 't'], explode_str)

    def test_insert_hidden_ids(self):
        app_dict = {'?': {
            'type': 'test.App',
            'id': '123'
            }
        }
        app_list = [1, 2, 3, 4]

        dict_result = helpers.insert_hidden_ids(app_dict)
        list_result = helpers.insert_hidden_ids(app_list)
        self.assertEqual('test.App', dict_result['?']['type'])
        self.assertEqual(app_list, list_result)
