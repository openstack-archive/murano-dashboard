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

from muranoclient.common import exceptions as exc
from muranodashboard.packages import tables


class TestImportPackage(testtools.TestCase):

    def setUp(self):
        super(TestImportPackage, self).setUp()

        self.import_package = tables.ImportPackage()

        self.assertEqual('upload_package', self.import_package.name)
        self.assertEqual('Import Package',
                         self.import_package.verbose_name)
        self.assertEqual('horizon:app-catalog:packages:upload',
                         self.import_package.url)
        self.assertEqual(('ajax-modal',), self.import_package.classes)
        self.assertEqual('plus', self.import_package.icon)
        self.assertEqual((('murano', 'upload_package'),),
                         self.import_package.policy_rules)

    @mock.patch.object(tables, 'api')
    def test_allowed(self, mock_api):
        mock_api.muranoclient().categories.list.return_value = ['foo_cat']
        self.assertTrue(self.import_package.allowed(None, None))

        mock_api.muranoclient().categories.list.return_value = None
        self.assertFalse(self.import_package.allowed(None, None))


class TestDownloadPackage(testtools.TestCase):

    def setUp(self):
        super(TestDownloadPackage, self).setUp()

        self.download_package = tables.DownloadPackage()

        self.assertEqual('download_package', self.download_package.name)
        self.assertEqual('Download Package',
                         self.download_package.verbose_name)
        self.assertEqual((('murano', 'download_package'),),
                         self.download_package.policy_rules)
        self.assertEqual('horizon:app-catalog:packages:download',
                         self.download_package.url)

    def test_allowed(self):
        self.assertTrue(self.download_package.allowed(None, None))

    @mock.patch.object(tables, 'reverse')
    def test_get_link_url(self, mock_reverse):
        mock_reverse.return_value = 'foo_reverse_url'
        mock_app = mock.Mock(id='foo_app_id')
        mock_app.configure_mock(name='FOO APP')

        result = self.download_package.get_link_url(mock_app)

        self.assertEqual('foo_reverse_url', result)
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:download',
            args=('foo-app', 'foo_app_id'))


class TestToggleEnabled(testtools.TestCase):

    def setUp(self):
        super(TestToggleEnabled, self).setUp()

        self.mock_request = mock.Mock()
        self.toggle_enabled = tables.ToggleEnabled()
        self.toggle_enabled.request = self.mock_request

        self.assertEqual('toggle_enabled', self.toggle_enabled.name)
        self.assertEqual('Toggle Enabled', self.toggle_enabled.verbose_name)
        self.assertEqual('toggle-on', self.toggle_enabled.icon)
        self.assertEqual((('murano', 'modify_package'),),
                         self.toggle_enabled.policy_rules)

    def test_action_present(self):
        self.assertEqual('Toggle Active',
                         tables.ToggleEnabled.action_present(1))
        self.assertEqual('Toggle Active',
                         tables.ToggleEnabled.action_present(2))

    def test_action_past(self):
        self.assertEqual('Toggled Active',
                         tables.ToggleEnabled.action_past(1))
        self.assertEqual('Toggled Active',
                         tables.ToggleEnabled.action_past(2))

    @mock.patch.object(tables, 'LOG')
    @mock.patch.object(tables, 'api')
    def test_action(self, mock_api, mock_log):
        self.toggle_enabled.action(self.mock_request, 'foo_package_id')

        mock_api.muranoclient().packages.toggle_active.assert_called_once_with(
            'foo_package_id')
        mock_log.debug.assert_called_once_with('Toggle Active for package '
                                               'foo_package_id.')

    @mock.patch.object(tables, 'reverse')
    @mock.patch.object(tables, 'messages')
    @mock.patch.object(tables, 'exceptions')
    @mock.patch.object(tables, 'LOG')
    @mock.patch.object(tables, 'api')
    def test_action_except_http_forbidden(self, mock_api, mock_log, mock_exc,
                                          mock_messages, mock_reverse):
        mock_api.muranoclient().packages.toggle_active.side_effect = \
            exc.HTTPForbidden
        mock_reverse.return_value = 'foo_reverse_url'
        expected_msg = _('You are not allowed to perform this operation')

        self.toggle_enabled.action(self.mock_request, 'foo_package_id')

        mock_api.muranoclient().packages.toggle_active.assert_called_once_with(
            'foo_package_id')
        mock_log.exception.assert_called_once_with(expected_msg)
        mock_messages.error.assert_called_once_with(self.mock_request,
                                                    expected_msg)
        mock_exc.handle.assert_called_once_with(self.mock_request,
                                                expected_msg,
                                                redirect='foo_reverse_url')
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')


class TestTogglePublicEnabled(testtools.TestCase):

    def setUp(self):
        super(TestTogglePublicEnabled, self).setUp()

        self.mock_request = mock.Mock()
        self.toggle_public_enabled = tables.TogglePublicEnabled()
        self.toggle_public_enabled.request = self.mock_request

        self.assertEqual('toggle_public_enabled',
                         self.toggle_public_enabled.name)
        self.assertEqual('share-alt', self.toggle_public_enabled.icon)
        self.assertEqual((('murano', 'publicize_package'),),
                         self.toggle_public_enabled.policy_rules)

    def test_action_present(self):
        self.assertEqual('Toggle Public',
                         tables.TogglePublicEnabled.action_present(1))
        self.assertEqual('Toggle Public',
                         tables.TogglePublicEnabled.action_present(2))

    def test_action_past(self):
        self.assertEqual('Toggled Public',
                         tables.TogglePublicEnabled.action_past(1))
        self.assertEqual('Toggled Public',
                         tables.TogglePublicEnabled.action_past(2))

    @mock.patch.object(tables, 'LOG')
    @mock.patch.object(tables, 'api')
    def test_action(self, mock_api, mock_log):
        self.toggle_public_enabled.action(self.mock_request, 'foo_package_id')

        mock_api.muranoclient().packages.toggle_public.assert_called_once_with(
            'foo_package_id')
        mock_log.debug.assert_called_once_with(
            'Toggle Public for package foo_package_id.')

    @mock.patch.object(tables, 'reverse')
    @mock.patch.object(tables, 'messages')
    @mock.patch.object(tables, 'exceptions')
    @mock.patch.object(tables, 'LOG')
    @mock.patch.object(tables, 'api')
    def test_action_except_http_forbidden(self, mock_api, mock_log, mock_exc,
                                          mock_messages, mock_reverse):
        mock_api.muranoclient().packages.toggle_public.side_effect = \
            exc.HTTPForbidden
        mock_reverse.return_value = 'foo_reverse_url'
        expected_msg = _('You are not allowed to perform this operation')

        self.toggle_public_enabled.action(self.mock_request, 'foo_package_id')

        mock_api.muranoclient().packages.toggle_public.assert_called_once_with(
            'foo_package_id')
        mock_log.exception.assert_called_once_with(expected_msg)
        mock_messages.error.assert_called_once_with(self.mock_request,
                                                    expected_msg)
        mock_exc.handle.assert_called_once_with(self.mock_request,
                                                expected_msg,
                                                redirect='foo_reverse_url')
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')

    @mock.patch.object(tables, 'reverse')
    @mock.patch.object(tables, 'messages')
    @mock.patch.object(tables, 'exceptions')
    @mock.patch.object(tables, 'LOG')
    @mock.patch.object(tables, 'api')
    def test_action_except_http_conflict(self, mock_api, mock_log, mock_exc,
                                         mock_messages, mock_reverse):
        mock_api.muranoclient().packages.toggle_public.side_effect = \
            exc.HTTPConflict
        mock_reverse.return_value = 'foo_reverse_url'
        expected_msg = _('Package or Class with the same name is already made '
                         'public')

        self.toggle_public_enabled.action(self.mock_request, 'foo_package_id')

        mock_api.muranoclient().packages.toggle_public.assert_called_once_with(
            'foo_package_id')
        mock_log.exception.assert_called_once_with(expected_msg)
        mock_messages.error.assert_called_once_with(self.mock_request,
                                                    expected_msg)
        mock_exc.handle.assert_called_once_with(self.mock_request,
                                                expected_msg,
                                                redirect='foo_reverse_url')
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')


class TestDeletePackage(testtools.TestCase):

    def setUp(self):
        super(TestDeletePackage, self).setUp()

        self.mock_request = mock.Mock()
        self.delete_package = tables.DeletePackage()
        self.delete_package.request = self.mock_request

        self.assertEqual('delete_package', self.delete_package.name)
        self.assertEqual((('murano', 'delete_package'),),
                         self.delete_package.policy_rules)

    def test_action_present(self):
        self.assertEqual('Delete Package',
                         tables.DeletePackage.action_present(1))
        self.assertEqual('Delete Packages',
                         tables.DeletePackage.action_present(2))

    def test_action_past(self):
        self.assertEqual('Deleted Package',
                         tables.DeletePackage.action_past(1))
        self.assertEqual('Deleted Packages',
                         tables.DeletePackage.action_past(2))

    @mock.patch.object(tables, 'LOG')
    @mock.patch.object(tables, 'api')
    def test_delete(self, mock_api, mock_log):

        self.delete_package.delete(self.mock_request, 'foo_package_id')

        mock_api.muranoclient().packages.delete.assert_called_once_with(
            'foo_package_id')
        mock_log.exception.assert_not_called()

    @mock.patch.object(tables, 'reverse')
    @mock.patch.object(tables, 'exceptions')
    @mock.patch.object(tables, 'LOG')
    @mock.patch.object(tables, 'api')
    def test_delete_except_http_not_found(self, mock_api, mock_log, mock_exc,
                                          mock_reverse):
        mock_api.muranoclient().packages.delete.side_effect = exc.HTTPNotFound
        mock_reverse.return_value = 'foo_reverse_url'
        expected_msg = _('Package with id foo_package_id is not found')

        self.delete_package.delete(self.mock_request, 'foo_package_id')

        mock_api.muranoclient().packages.delete.assert_called_once_with(
            'foo_package_id')
        mock_log.exception.assert_called_once_with(expected_msg)
        mock_exc.handle.assert_called_once_with(self.mock_request,
                                                expected_msg,
                                                redirect='foo_reverse_url')
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')

    @mock.patch.object(tables, 'reverse')
    @mock.patch.object(tables, 'exceptions')
    @mock.patch.object(tables, 'LOG')
    @mock.patch.object(tables, 'api')
    def test_delete_except_http_forbidden(self, mock_api, mock_log, mock_exc,
                                          mock_reverse):
        mock_api.muranoclient().packages.delete.side_effect = exc.HTTPForbidden
        mock_reverse.return_value = 'foo_reverse_url'
        expected_msg = _('You are not allowed to delete this package')

        self.delete_package.delete(self.mock_request, 'foo_package_id')

        mock_api.muranoclient().packages.delete.assert_called_once_with(
            'foo_package_id')
        mock_log.exception.assert_called_once_with(expected_msg)
        mock_exc.handle.assert_called_once_with(self.mock_request,
                                                expected_msg,
                                                redirect='foo_reverse_url')
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')

    @mock.patch.object(tables, 'reverse')
    @mock.patch.object(tables, 'exceptions')
    @mock.patch.object(tables, 'LOG')
    @mock.patch.object(tables, 'api')
    def test_delete_except_exception(self, mock_api, mock_log, mock_exc,
                                     mock_reverse):
        mock_api.muranoclient().packages.delete.side_effect = Exception
        mock_reverse.return_value = 'foo_reverse_url'
        expected_log_msg = _('Unable to delete package in murano-api server')

        self.delete_package.delete(self.mock_request, 'foo_package_id')

        mock_api.muranoclient().packages.delete.assert_called_once_with(
            'foo_package_id')
        mock_log.exception.assert_called_once_with(expected_log_msg)
        mock_exc.handle.assert_called_once_with(self.mock_request,
                                                _('Unable to remove package.'),
                                                redirect='foo_reverse_url')
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')


class TestModifyPackage(testtools.TestCase):

    def setUp(self):
        super(TestModifyPackage, self).setUp()

        self.modify_package = tables.ModifyPackage()

        self.assertEqual('modify_package', self.modify_package.name)
        self.assertEqual(_('Modify Package'),
                         self.modify_package.verbose_name)
        self.assertEqual('horizon:app-catalog:packages:modify',
                         self.modify_package.url)
        self.assertEqual(('ajax-modal',), self.modify_package.classes)
        self.assertEqual('edit', self.modify_package.icon)
        self.assertEqual((('murano', 'modify_package'),),
                         self.modify_package.policy_rules)

    def test_allowed(self):
        self.assertTrue(self.modify_package.allowed(None, None))
