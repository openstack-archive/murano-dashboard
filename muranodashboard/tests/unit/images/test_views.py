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

import json
import mock
import testtools

from horizon import exceptions

from muranodashboard.images import tables
from muranodashboard.images import views


class TestMarkedImagesView(testtools.TestCase):

    def setUp(self):
        super(TestMarkedImagesView, self).setUp()

        mock_request = mock.Mock(horizon={'async_messages': []})
        self.images_view = views.MarkedImagesView(request=mock_request)
        self.images_view._prev = False
        self.images_view._more = False

        self.assertEqual(tables.MarkedImagesTable,
                         self.images_view.table_class)
        self.assertEqual('images/index.html', self.images_view.template_name)
        self.assertEqual('Marked Images', self.images_view.page_title)

        mock_horizon_utils = mock.patch.object(views, 'utils').start()
        mock_horizon_utils.get_page_size.return_value = 2
        self.addCleanup(mock.patch.stopall)

    def _get_mock_image(self, prefix):
        image_info = {}
        if prefix:
            image_info = {
                "title": "{0}_title".format(prefix),
                "type": "{0}_type".format(prefix)
            }
        mock_image = mock.Mock(**{'murano_image_info': json.dumps(image_info)})
        return mock_image

    def test_has_prev_data(self):
        self.assertFalse(self.images_view.has_prev_data(None))

    def test_has_more_data(self):
        self.assertFalse(self.images_view.has_more_data(None))

    @mock.patch.object(views, 'glance', autospec=True)
    def test_get_data(self, mock_glance):
        """Test that get_data works."""
        foo_mock_image = self._get_mock_image('foo')
        bar_mock_image = self._get_mock_image('bar')
        # Filtered out by forms.filter_murano_images.
        mock_image_to_filter = self._get_mock_image(None)

        mock_glance_client = mock.Mock()
        mock_glance_client.images.list.return_value = [
            foo_mock_image, bar_mock_image, mock_image_to_filter]
        mock_glance.glanceclient.return_value = mock_glance_client

        self.images_view.request.GET.get.return_value = 'foo_marker'
        result = self.images_view.get_data()

        expected_images = [bar_mock_image, foo_mock_image]
        expected_kwargs = {
            'filters': {},
            'marker': 'foo_marker',
            'sort_dir': 'asc'
        }

        self.assertEqual(expected_images, result)
        self.assertTrue(self.images_view.has_more_data(None))
        self.assertTrue(self.images_view.has_prev_data(None))
        mock_glance_client.images.list.assert_called_once_with(
            **expected_kwargs)
        self.images_view.request.GET.get.assert_called_once_with(
            tables.MarkedImagesTable._meta.prev_pagination_param, None)
        mock_glance.glanceclient.assert_called_once_with(
            self.images_view.request, "2")

    @mock.patch.object(views, 'glance', autospec=True)
    def test_get_data_with_desc_sort_dir(self, mock_glance):
        """Test that sorting in descending order works."""
        foo_mock_image = self._get_mock_image('foo')
        bar_mock_image = self._get_mock_image('bar')

        mock_glance_client = mock.Mock()
        mock_glance_client.images.list.return_value = [
            foo_mock_image, bar_mock_image]
        mock_glance.glanceclient.return_value = mock_glance_client

        self.images_view.request.GET.get.return_value = None
        result = self.images_view.get_data()

        expected_images = [foo_mock_image, bar_mock_image]
        expected_kwargs = {
            'filters': {},
            'sort_dir': 'desc'
        }

        self.assertEqual(expected_images, result)
        self.assertFalse(self.images_view.has_more_data(None))
        self.assertFalse(self.images_view.has_prev_data(None))
        mock_glance_client.images.list.assert_called_once_with(
            **expected_kwargs)
        self.images_view.request.GET.get.assert_has_calls([
            mock.call(tables.MarkedImagesTable._meta.prev_pagination_param,
                      None),
            mock.call(tables.MarkedImagesTable._meta.pagination_param, None)
        ])
        mock_glance.glanceclient.assert_called_once_with(
            self.images_view.request, "2")

    @mock.patch.object(views, 'glance', autospec=True)
    def test_get_data_with_more_results(self, mock_glance):
        """Test that extra results are not included in return value."""
        foo_mock_image = self._get_mock_image('foo')
        bar_mock_image = self._get_mock_image('bar')
        extra_mock_image = self._get_mock_image('baz')  # Extra result.
        # Filtered out by forms.filter_murano_images.
        mock_image_to_filter = self._get_mock_image(None)

        mock_glance_client = mock.Mock()
        mock_glance_client.images.list.return_value = [
            foo_mock_image, bar_mock_image, extra_mock_image,
            mock_image_to_filter]
        mock_glance.glanceclient.return_value = mock_glance_client

        self.images_view.request.GET.get.return_value = 'foo_marker'
        result = self.images_view.get_data()

        # Extra result not included, and result should be reversed.
        expected_images = [bar_mock_image, foo_mock_image]
        expected_kwargs = {
            'filters': {},
            'marker': 'foo_marker',
            'sort_dir': 'asc'
        }

        self.assertEqual(expected_images, result)
        self.assertTrue(self.images_view.has_more_data(None))
        self.assertTrue(self.images_view.has_prev_data(None))
        mock_glance_client.images.list.assert_called_once_with(
            **expected_kwargs)
        self.images_view.request.GET.get.assert_called_once_with(
            tables.MarkedImagesTable._meta.prev_pagination_param, None)
        mock_glance.glanceclient.assert_called_once_with(
            self.images_view.request, "2")

    @mock.patch.object(views, 'reverse', autospec=True)
    @mock.patch.object(views, 'glance', autospec=True)
    def test_get_data_except_glance_image_list_exception(self, mock_glance,
                                                         mock_reverse):
        """Test that glance_v1_client.images.list exception is handled."""
        mock_glance_client = mock.Mock()
        mock_glance_client.images.list.side_effect = Exception()
        mock_glance.glanceclient.return_value = mock_glance_client
        mock_reverse.return_value = 'foo_reverse_url'
        self.images_view.request.GET.get.return_value = None

        e = self.assertRaises(exceptions.Http302, self.images_view.get_data)
        self.assertEqual('foo_reverse_url', e.location)

        mock_glance.glanceclient.assert_called_once_with(
            self.images_view.request, "2")
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:catalog:index')
