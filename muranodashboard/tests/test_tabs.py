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

import mock

from muranodashboard.catalog import tabs
from openstack_dashboard.test import helpers


class TestLicenseTab(helpers.APITestCase):
    def setUp(self):
        """Set up the Form data."""
        super(TestLicenseTab, self).setUp()

    @mock.patch('muranodashboard.catalog.tabs.services')
    def test_license(self, mock_services):
        """Check that a license is returned."""

        # Fake the services.get_app_forms() call.
        m = mock.MagicMock()
        m.base_fields = {
            'license': mock.MagicMock(
                description='Lorem ipsum dolor sit '
                            'amet, consectetur adipiscing elit.')
        }
        mock_services.get_app_forms.return_value = [('', m)]

        # Fake an application object, needed when instantiating tabs.
        app = mock.MagicMock()
        app.id = 1

        group = tabs.ApplicationTabs(self.request, application=app)
        l = group.get_tabs()[2]

        # Should return the license description
        l._get_license()
        self.assertEqual(
            'Lorem ipsum dolor sit amet, consectetur adipiscing elit.',
            l.app.license)

    @mock.patch('muranodashboard.catalog.tabs.services')
    def test_no_license(self, mock_services):
        """Check that no license is returned."""

        # Fake the services.get_app_forms() call.
        m = mock.MagicMock()
        m.base_fields = {}
        mock_services.get_app_forms.return_value = [('', m)]

        # Fake an application object, needed when instantiating tabs.
        app = mock.MagicMock()
        app.id = 1

        group = tabs.ApplicationTabs(self.request, application=app)
        l = group.get_tabs()[2]

        # Should return the license description
        l._get_license()
        self.assertEqual('', l.app.license)


class TestRequirementsTab(helpers.APITestCase):
    def setUp(self):
        """Set up the Form data."""
        super(TestRequirementsTab, self).setUp()

    @mock.patch('muranodashboard.catalog.tabs.services')
    def test_requirements(self, mock_services):
        """Check that requirements are returned."""

        m = mock.MagicMock()
        m.base_fields = {
            'flavor': mock.MagicMock(requirements={
                'min_disk': 10,
                'min_vcpus': 2,
                'min_memory_mb': 2048,
                'max_disk': 25,
                'max_vcpus': 5,
                'max_memory_mb': 16000,
            })
        }
        mock_services.get_app_forms.return_value = [('', m)]

        app = mock.MagicMock()
        app.id = 1

        group = tabs.ApplicationTabs(self.request, application=app)
        r = group.get_tabs()[1]

        # Should return the requirements list used by the template file.
        r._get_requirements()

        self.assertIn('Instance flavor:', r.app.requirements)
        flavor_req = r.app.requirements[1]

        self.assertIn('Minimum disk size: 10 GB',
                      flavor_req)
        self.assertIn('Minimum vCPUs: 2',
                      flavor_req)
        self.assertIn('Minimum RAM size: 2048 MB',
                      flavor_req)
        self.assertIn('Maximum disk size: 25 GB',
                      flavor_req)
        self.assertIn('Maximum vCPUs: 5',
                      flavor_req)
        self.assertIn('Maximum RAM size: 16000 MB',
                      flavor_req)

    @mock.patch('muranodashboard.catalog.tabs.services')
    def test_no_requirements(self, mock_services):
        """Check that no requirements are returned."""

        m = mock.MagicMock()
        m.base_fields = {}
        mock_services.get_app_forms.return_value = [('', m)]

        app = mock.MagicMock()
        app.id = 1

        group = tabs.ApplicationTabs(self.request, application=app)
        r = group.get_tabs()[1]

        # Should return an empty requirements list
        r._get_requirements()
        self.assertListEqual([], r.app.requirements)
