#    Copyright (c) 2014 Mirantis, Inc.
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

from muranodashboard.common import utils


class BunchTests(testtools.TestCase):
    def test_get_attr(self):
        obj = utils.Bunch(one=10)

        self.assertEqual(10, obj.one)

    def test_get_item(self):
        obj = utils.Bunch(two=15)

        self.assertEqual(15, obj['two'])

    def test_in(self):
        obj = utils.Bunch(one=10)

        self.assertIn('one', obj)

    def test_iteration(self):
        obj = utils.Bunch(one=10, two=15)

        sorted_objs = sorted([o for o in obj])

        self.assertEqual([10, 15], sorted_objs)

    def test_set_attr(self):
        obj = utils.Bunch()

        obj.one = 10

        self.assertEqual(10, obj['one'])

    def test_set_item(self):
        obj = utils.Bunch()

        obj['two'] = 20

        self.assertEqual(20, obj['two'])

    def test_del_attr(self):
        obj = utils.Bunch(one=10)

        del obj.one

        self.assertNotIn('one', obj)

    def test_del_item(self):
        obj = utils.Bunch(two=20)

        del obj['two']

        self.assertNotIn('two', obj)
