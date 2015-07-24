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

from muranodashboard.dynamic_ui import fields
from openstack_dashboard.test import helpers


class TestFlavorField(helpers.APITestCase):
    def setUp(self):
        """Set up the Flavor Class and novaclient."""
        super(TestFlavorField, self).setUp()

        class FlavorFlave(object):
            def __init__(self, name, vcpus, disk, ram):
                self.name = name
                self.vcpus = vcpus
                self.disk = disk
                self.ram = ram

        novaclient = self.stub_novaclient()
        novaclient.flavors = self.mox.CreateMockAnything()
        # Set up the Flavor list
        novaclient.flavors.list().MultipleTimes().AndReturn(
            [FlavorFlave('small', vcpus=1, disk=50, ram=1000),
             FlavorFlave('medium', vcpus=2, disk=100, ram=2000),
             FlavorFlave('large', vcpus=3, disk=750, ram=4000)])

    def test_no_filter(self):
        """Check that all flavors are returned."""

        self.mox.ReplayAll()

        # No requirements, should return all flavors
        f = fields.FlavorChoiceField()
        initial_request = {}
        f.update(initial_request, self.request)
        self.assertEqual(
            [('small', 'small'),
             ('medium', 'medium'),
             ('large', 'large')],
            f.choices)

    def test_multiple_filter(self):
        """Check that 2 flavors are returned."""

        self.mox.ReplayAll()

        # Fake a requirement for 2 CPUs, should return medium and large
        f = fields.FlavorChoiceField(requirements={'min_vcpus': 2})
        initial_request = {}
        f.update(initial_request, self.request)
        self.assertEqual([('medium', 'medium'), ('large', 'large')], f.choices)

    def test_single_filter(self):
        """Check that one flavor is returned."""
        self.mox.ReplayAll()

        # Fake a requirement for 2 CPUs and 200 GB disk, should return medium
        f = fields.FlavorChoiceField(
            requirements={'min_vcpus': 2, 'min_disk': 200})
        initial_request = {}
        f.update(initial_request, self.request)
        self.assertEqual([('large', 'large')], f.choices)

    def test_no_matches_filter(self):
        """Check that no flavors are returned."""
        self.mox.ReplayAll()

        # Fake a requirement for 4 CPUs, should return no flavors
        f = fields.FlavorChoiceField(requirements={'min_vcpus': 4})
        initial_request = {}
        f.update(initial_request, self.request)
        self.assertEqual([], f.choices)
