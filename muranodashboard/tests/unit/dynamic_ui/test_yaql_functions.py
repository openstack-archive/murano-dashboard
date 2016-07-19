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

import re
import testtools

from muranodashboard.dynamic_ui import yaql_functions


class TestYAQLFunctions(testtools.TestCase):

    def test_generate_hostname(self):
        self.assertEqual(
            yaql_functions._generate_hostname('foo-#', 1), 'foo-1')
        self.assertEqual(
            yaql_functions._generate_hostname('foo-#', 22), 'foo-22')

    def test_generate_hostname_random(self):
        random = yaql_functions._generate_hostname('', 3)
        self.assertTrue(bool(re.match(r'^\w{14}$', random)))
