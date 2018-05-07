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

from django.core import exceptions

from muranodashboard.dynamic_ui import fields
from openstack_dashboard.test import helpers

import mock


class FlavorFlave(object):
    def __init__(self, id, name, vcpus, disk, ram):
        self.name = name
        self.vcpus = vcpus
        self.disk = disk
        self.ram = ram
        self.id = id


class TestFlavorField(helpers.APIMockTestCase):

    @mock.patch('muranodashboard.dynamic_ui.fields.nova')
    def test_no_filter(self, mock_nova):

        # No requirements, should return all flavors
        mock_nova.novaclient().flavors.list.return_value = [
            FlavorFlave('id1', 'small', vcpus=1, disk=50, ram=1000),
            FlavorFlave('id2', 'medium', vcpus=2, disk=100, ram=2000),
            FlavorFlave('id3', 'large',  vcpus=3, disk=750, ram=4000)]

        f = fields.FlavorChoiceField()
        initial_request = {}
        f.update(initial_request, self.request)
        self.assertEqual([
            ('id3', 'large'),
            ('id2', 'medium'),
            ('id1', 'small')
        ], f.choices)

    @mock.patch('muranodashboard.dynamic_ui.fields.nova')
    def test_multiple_filter(self, mock_nova):

        mock_nova.novaclient().flavors.list.return_value = [
            FlavorFlave('id2', 'medium', vcpus=2, disk=100, ram=2000),
            FlavorFlave('id3', 'large',  vcpus=3, disk=750, ram=4000)]

        f = fields.FlavorChoiceField(requirements={'min_vcpus': 2})
        f.update({}, self.request)
        self.assertEqual([('id3', 'large'), ('id2', 'medium')], f.choices)

    @mock.patch('muranodashboard.dynamic_ui.fields.nova')
    def test_single_filter(self, mock_nova):

        """Check that one flavor is returned."""
        mock_nova.novaclient().flavors.list.return_value = [
            FlavorFlave('id3', 'large', vcpus=3, disk=750, ram=4000)]

        # Fake a requirement for 2 CPUs and 200 GB disk, should return large
        f = fields.FlavorChoiceField(
            requirements={'min_vcpus': 2, 'min_disk': 200})
        initial_request = {}
        f.update(initial_request, self.request)
        self.assertEqual([('id3', 'large')], f.choices)

    @mock.patch('muranodashboard.dynamic_ui.fields.nova')
    def test_no_matches_filter(self, mock_nova):

        mock_nova.novaclient().flavors.list.return_value = []

        # Fake a requirement for 4 CPUs, should return no flavors
        f = fields.FlavorChoiceField(requirements={'min_vcpus': 4})
        initial_request = {}
        f.update(initial_request, self.request)
        self.assertEqual([], f.choices)


class TestPasswordField(helpers.TestCase):
    def test_valid_input(self):
        f = fields.PasswordField('')
        for char in f.special_characters:
            if char != '\\':
                password = 'aA1111' + char
                self.assertIsNone(f.run_validators(password))

    def test_short_input(self):
        f = fields.PasswordField('')
        password = 'aA@111'
        self.assertRaises(exceptions.ValidationError, f.run_validators,
                          password)

    def test_input_without_special_characters(self):
        f = fields.PasswordField('')
        password = 'aA11111'
        self.assertRaises(exceptions.ValidationError, f.run_validators,
                          password)

    def test_input_without_digits(self):
        f = fields.PasswordField('')
        password = 'aA@@@@@'
        self.assertRaises(exceptions.ValidationError, f.run_validators,
                          password)

    def test_input_without_lowecase(self):
        f = fields.PasswordField('')
        password = 'A1@@@@@'
        self.assertRaises(exceptions.ValidationError, f.run_validators,
                          password)

    def test_input_without_uppercase(self):
        f = fields.PasswordField('')
        password = 'a1@@@@@'
        self.assertRaises(exceptions.ValidationError, f.run_validators,
                          password)
