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

from django.utils.translation import ugettext_lazy as _

from muranodashboard.images import forms


class TestImagesForms(testtools.TestCase):
    def setUp(self):
        super(TestImagesForms, self).setUp()
        metadata = '{"title": "title", "type": "type"}'
        self.mock_img = mock.MagicMock(id=12, murano_image_info=metadata)
        self.mock_request = mock.MagicMock()

    @mock.patch.object(forms, 'LOG')
    def test_filter_murano_images(self, mock_log):
        mock_blank_img = \
            mock.MagicMock(id=13, murano_image_info="info")
        images = [mock_blank_img]
        msg = _('Invalid metadata for image: {0}').format(images[0].id)
        self.assertEqual(images,
                         forms.filter_murano_images(images, self.mock_request))
        mock_log.warning.assert_called_once_with(msg)

        images = [self.mock_img]
        self.assertEqual(images, forms.filter_murano_images(images))

        murano_meta = '{"title": "title", "type": "type"}'

        mock_snapshot_img = mock.MagicMock(
            id=14, murano_image_info=murano_meta, image_type='snapshot')
        images = [mock_snapshot_img]
        self.assertEqual([],
                         forms.filter_murano_images(images, self.mock_request))


class TestMarkImageForm(testtools.TestCase):
    def setUp(self):
        super(TestMarkImageForm, self).setUp()
        self.mock_request = mock.MagicMock()
        self.mark_img_form = forms.MarkImageForm(self.mock_request)

    @mock.patch.object(forms, 'glance')
    def test_handle(self, mock_glance_api):
        data = {
            'title': 'title',
            'image': 'id',
            'type': 'type'
        }
        self.mark_img_form.handle(self.mock_request, data)
        self.assertTrue(mock_glance_api.image_update_properties.called)
