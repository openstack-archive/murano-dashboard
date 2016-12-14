# Copyright (c) 2016 AT&T Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
import testtools

from muranodashboard.categories import tables
from muranodashboard.categories import views


class TestCategoriesView(testtools.TestCase):

    def setUp(self):
        super(TestCategoriesView, self).setUp()

        self.categories_view = views.CategoriesView()
        self.categories_view._prev = False
        self.categories_view._more = False

        mock_request = mock.Mock()
        self.categories_view.request = mock_request

        self.assertEqual(tables.CategoriesTable,
                         self.categories_view.table_class)
        self.assertEqual('categories/index.html',
                         self.categories_view.template_name)
        self.assertEqual('Application Categories',
                         self.categories_view.page_title)

        mock_horizon_utils = mock.patch.object(views, 'utils').start()
        mock_horizon_utils.get_page_size.return_value = 2
        self.addCleanup(mock.patch.stopall)

    def test_has_prev_data(self):
        self.assertFalse(self.categories_view.has_prev_data(None))

    def test_has_more_data(self):
        self.assertFalse(self.categories_view.has_more_data(None))

    @mock.patch.object(views, 'api', autospec=True)
    def test_get_data(self, mock_api):
        """Test that get_data works."""
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.categories.list.return_value = [
            'foo_cat', 'bar_cat'
        ]
        self.categories_view.request.GET.get.return_value = 'foo_marker'

        result = self.categories_view.get_data()

        expected_categories = ['bar_cat', 'foo_cat']
        expected_kwargs = {
            'filters': {},
            'marker': 'foo_marker',
            'sort_dir': 'asc',
            'limit': 3
        }

        self.assertEqual(expected_categories, result)
        self.assertTrue(self.categories_view.has_more_data(None))
        self.assertFalse(self.categories_view.has_prev_data(None))
        self.categories_view.request.GET.get.assert_called_once_with(
            tables.CategoriesTable._meta.prev_pagination_param, None)
        mock_client.categories.list.assert_called_once_with(
            **expected_kwargs)

    @mock.patch.object(views, 'api', autospec=True)
    def test_get_data_with_more_results(self, mock_api):
        """Test that get_data with pagesize smaller than result size works."""
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.categories.list.return_value = [
            'foo_cat', 'bar_cat', 'baz_cat'
        ]
        self.categories_view.request.GET.get.return_value = 'foo_marker'

        result = self.categories_view.get_data()

        # Only two results should have been returned, with categories reversed.
        expected_categories = ['bar_cat', 'foo_cat']
        expected_kwargs = {
            'filters': {},
            'marker': 'foo_marker',
            'sort_dir': 'asc',
            'limit': 3
        }

        self.assertEqual(expected_categories, result)
        self.assertTrue(self.categories_view.has_more_data(None))
        self.assertTrue(self.categories_view.has_prev_data(None))
        self.categories_view.request.GET.get.assert_called_once_with(
            tables.CategoriesTable._meta.prev_pagination_param, None)
        mock_client.categories.list.assert_called_once_with(
            **expected_kwargs)

    @mock.patch.object(views, 'api', autospec=True)
    def test_get_data_with_desc_sort_dir(self, mock_api):
        """Test that get_data with sort_dir = 'desc' works."""
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.categories.list.return_value = [
            'foo_cat', 'bar_cat'
        ]
        self.categories_view.request.GET.get.side_effect = [None, 'bar_marker']

        result = self.categories_view.get_data()

        expected_categories = ['foo_cat', 'bar_cat']
        expected_kwargs = {
            'filters': {},
            'marker': 'bar_marker',
            'sort_dir': 'desc',
            'limit': 3
        }

        self.assertEqual(expected_categories, result)
        self.assertFalse(self.categories_view.has_more_data(None))
        self.assertTrue(self.categories_view.has_prev_data(None))
        self.categories_view.request.GET.get.assert_has_calls([
            mock.call(tables.CategoriesTable._meta.prev_pagination_param,
                      None),
            mock.call(tables.CategoriesTable._meta.pagination_param, None)
        ])
        mock_client.categories.list.assert_called_once_with(
            **expected_kwargs)
