#    Copyright (c) 2013 Mirantis, Inc.
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

from django.template import defaultfilters
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from horizon import exceptions
from horizon import messages
from horizon import tables
from horizon.utils import filters
from openstack_dashboard import policy
from oslo_log import log as logging

from muranoclient.common import exceptions as exc
from muranodashboard import api
from muranodashboard.common import utils as md_utils

LOG = logging.getLogger(__name__)


class ImportBundle(tables.LinkAction):
    name = 'import_bundle'
    verbose_name = _('Import Bundle')
    url = 'horizon:app-catalog:packages:import_bundle'
    classes = ('ajax-modal',)
    icon = "plus"
    policy_rules = (("murano", "upload_package"),)


class ImportPackage(tables.LinkAction):
    name = 'upload_package'
    verbose_name = _('Import Package')
    url = 'horizon:app-catalog:packages:upload'
    classes = ('ajax-modal',)
    icon = "plus"
    policy_rules = (("murano", "upload_package"),)

    def allowed(self, request, package):
        _allowed = False
        with api.handled_exceptions(request):
            client = api.muranoclient(request)
            if client.categories.list():
                _allowed = True
        return _allowed


class PackagesFilterAction(tables.FilterAction):
    name = "filter_packages"
    filter_type = "server"
    filter_choices = (('search', _("KeyWord"), True),
                      ('type', _("Type"), True),
                      ('name', _("Name"), True))


class DownloadPackage(tables.LinkAction):
    name = 'download_package'
    verbose_name = _('Download Package')
    policy_rules = (("murano", "download_package"),)
    url = 'horizon:app-catalog:packages:download'

    def allowed(self, request, package):
        return True

    def get_link_url(self, app):
        app_name = defaultfilters.slugify(app.name)
        return reverse(self.url, args=(app_name, app.id))


class ToggleEnabled(tables.BatchAction):
    name = 'toggle_enabled'
    verbose_name = _("Toggle Enabled")
    icon = "toggle-on"
    policy_rules = (("murano", "modify_package"),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Toggle Active",
            u"Toggle Active",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Toggled Active",
            u"Toggled Active",
            count
        )

    def action(self, request, obj_id):
        try:
            api.muranoclient(request).packages.toggle_active(obj_id)
            LOG.debug('Toggle Active for package {0}.'.format(obj_id))
        except exc.HTTPForbidden:
            msg = _("You are not allowed to perform this operation")
            LOG.exception(msg)
            messages.error(request, msg)
            exceptions.handle(
                request,
                msg,
                redirect=reverse('horizon:app-catalog:packages:index'))


class TogglePublicEnabled(tables.BatchAction):
    name = 'toggle_public_enabled'
    verbose_name = _("Toggle Public")
    icon = "share-alt"
    policy_rules = (("murano", "publicize_package"),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Toggle Public",
            u"Toggle Public",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Toggled Public",
            u"Toggled Public",
            count
        )

    def action(self, request, obj_id):
        try:
            api.muranoclient(request).packages.toggle_public(obj_id)
            LOG.debug('Toggle Public for package {0}.'.format(obj_id))
        except exc.HTTPForbidden:
            msg = _("You are not allowed to perform this operation")
            LOG.exception(msg)
            messages.error(request, msg)
            exceptions.handle(
                request,
                msg,
                redirect=reverse('horizon:app-catalog:packages:index'))
        except exc.HTTPConflict:
            msg = _('Package or Class with the same name is already made '
                    'public')
            LOG.exception(msg)
            messages.error(request, msg)
            exceptions.handle(
                request,
                msg,
                redirect=reverse('horizon:app-catalog:packages:index'))


class DeletePackage(policy.PolicyTargetMixin, tables.DeleteAction):
    name = 'delete_package'
    policy_rules = (("murano", "delete_package"),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Package",
            u"Delete Packages",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Package",
            u"Deleted Packages",
            count
        )

    def delete(self, request, obj_id):
        try:
            api.muranoclient(request).packages.delete(obj_id)
        except exc.HTTPNotFound:
            msg = _("Package with id {0} is not found").format(obj_id)
            LOG.exception(msg)
            exceptions.handle(
                self.request,
                msg,
                redirect=reverse('horizon:app-catalog:packages:index'))
        except exc.HTTPForbidden:
            msg = _("You are not allowed to delete this package")
            LOG.exception(msg)
            exceptions.handle(
                request, msg,
                redirect=reverse('horizon:app-catalog:packages:index'))
        except Exception:
            LOG.exception(_('Unable to delete package in murano-api server'))
            url = reverse('horizon:app-catalog:packages:index')
            exceptions.handle(request,
                              _('Unable to remove package.'),
                              redirect=url)


class ModifyPackage(tables.LinkAction):
    name = 'modify_package'
    verbose_name = _('Modify Package')
    url = 'horizon:app-catalog:packages:modify'
    classes = ('ajax-modal',)
    icon = "edit"
    policy_rules = (("murano", "modify_package"),)

    def allowed(self, request, package):
        return True


class PackageDefinitionsTable(tables.DataTable):
    name = md_utils.Column(
        'name',
        link="horizon:app-catalog:packages:detail",
        verbose_name=_('Package Name'))
    tenant_name = tables.Column('tenant_name', verbose_name=_('Tenant Name'))
    enabled = tables.Column('enabled', verbose_name=_('Active'))
    is_public = tables.Column('is_public', verbose_name=_('Public'))
    type = tables.Column('type', verbose_name=_('Type'))
    version = tables.Column(lambda obj: getattr(obj, 'version', None),
                            verbose_name=_('Version'))
    created_time = tables.Column('created',
                                 verbose_name=_('Created'),
                                 filters=(filters.parse_isotime,))
    updated_time = tables.Column('updated',
                                 verbose_name=_('Updated'),
                                 filters=(filters.parse_isotime,))

    def get_prev_pagination_string(self):
        pagination_string = super(
            PackageDefinitionsTable, self).get_prev_pagination_string()
        return pagination_string + "&sort_dir=desc"

    class Meta(object):
        name = 'packages'
        prev_pagination_param = 'marker'
        verbose_name = _('Packages')
        table_actions_menu = (ToggleEnabled,
                              TogglePublicEnabled)
        table_actions = (PackagesFilterAction,
                         ImportPackage,
                         ImportBundle,
                         DeletePackage)

        row_actions = (ModifyPackage,
                       DownloadPackage,
                       ToggleEnabled,
                       TogglePublicEnabled,
                       DeletePackage)
