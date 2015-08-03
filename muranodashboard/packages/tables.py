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

from collections import defaultdict
import logging

from django.core.urlresolvers import reverse
from django import http
from django.template import defaultfilters
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from horizon import exceptions
from horizon import tables

from muranoclient.common import exceptions as exc
from muranodashboard import api

LOG = logging.getLogger(__name__)


class ImportBundle(tables.LinkAction):
    name = 'import_bundle'
    verbose_name = _('Import Bundle')
    url = 'horizon:murano:packages:import_bundle'
    classes = ('ajax-modal',)
    icon = "plus"


class ImportPackage(tables.LinkAction):
    name = 'upload_package'
    verbose_name = _('Import Package')
    url = 'horizon:murano:packages:upload'
    classes = ('ajax-modal',)
    icon = "plus"

    def allowed(self, request, image):
        _allowed = False
        with api.handled_exceptions(request):
            client = api.muranoclient(request)
            _allowed = client.packages.categories() is not None
        return _allowed


class DownloadPackage(tables.Action):
    name = 'download_package'
    verbose_name = _('Download Package')

    def allowed(self, request, image):
        return True

    @staticmethod
    def get_package_name(data_table, app_id):
        # TODO(tsufiev): should use more optimal search here
        name = None
        for pkg in data_table.data:
            if pkg.id == app_id:
                name = defaultfilters.slugify(pkg.name)
                break
        return name if name is not None else app_id

    def single(self, data_table, request, app_id):
        try:
            body = api.muranoclient(request).packages.download(app_id)

            content_type = 'application/octet-stream'
            response = http.HttpResponse(body, content_type=content_type)
            response['Content-Disposition'] = 'filename={name}.zip'.format(
                name=self.get_package_name(data_table, app_id))
            return response
        except exc.HTTPException:
            LOG.exception(_('Something went wrong during package downloading'))
            redirect = reverse('horizon:murano:packages:index')
            exceptions.handle(request,
                              _('Unable to download package.'),
                              redirect=redirect)


class ToggleEnabled(tables.BatchAction):
    name = 'toggle_enabled'
    verbose_name = _("Toggle Enabled")

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
        api.muranoclient(request).packages.toggle_active(obj_id)


class TogglePublicEnabled(tables.BatchAction):
    name = 'toggle_public_enabled'
    verbose_name = _("Toggle Public")

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
        api.muranoclient(request).packages.toggle_public(obj_id)


class DeletePackage(tables.DeleteAction):
    name = 'delete_package'
    data_type_singular = _('Package')

    def delete(self, request, obj_id):
        try:
            api.muranoclient(request).packages.delete(obj_id)
        except exc.HTTPNotFound:
            msg = _("Package with id {0} is not found").format(obj_id)
            LOG.exception(msg)
            exceptions.handle(
                self.request,
                msg,
                redirect=reverse('horizon:murano:packages:index'))
        except exc.HTTPForbidden:
            msg = _("You are not allowed to delete this package")
            LOG.exception(msg)
            exceptions.handle(
                request, msg,
                redirect=reverse('horizon:murano:packages:index'))
        except Exception:
            LOG.exception(_('Unable to delete package in murano-api server'))
            exceptions.handle(request,
                              _('Unable to remove package.'),
                              redirect='horizon:murano:packages:index')


class ModifyPackage(tables.LinkAction):
    name = 'modify_package'
    verbose_name = _('Modify Package')
    url = 'horizon:murano:packages:modify'
    classes = ('ajax-modal',)
    icon = "edit"

    def allowed(self, request, environment):
        return True


def get_package_categories(pkg, user_tenant_id):
    categories = []
    if pkg.is_public:
        categories.append('public')
    if pkg.owner_id == user_tenant_id:
        categories.append('project')
    else:
        categories.append('other')
    return categories


class OwnerFilter(tables.FixedFilterAction):
    def get_fixed_buttons(self):
        def make_dict(text, tenant, icon):
            return dict(text=text, value=tenant, icon=icon)

        buttons = [make_dict(_('Project'), 'project', 'fa-home')]
        buttons.append(make_dict(_('Public'), 'public', 'fa-group'))
        buttons.append(make_dict(_('Other'), 'other', 'fa-cloud'))
        return buttons

    def categorize(self, table, packages):
        user_tenant_id = table.request.user.tenant_id
        tenants = defaultdict(list)
        for pkg in packages:
            categories = get_package_categories(pkg, user_tenant_id)
            for category in categories:
                tenants[category].append(pkg)
        # Other category is available only for admins.
        # So, hide it if it's empty.
        if 'other' not in tenants:
            for i, btn in enumerate(self.fixed_buttons):
                if btn['value'] == 'other':
                    del self.fixed_buttons[i]

        return tenants


class UpdateRow(tables.Row):
    ajax = True

    def get_data(self, request, package_id):
        package = api.muranoclient(request).packages.get(package_id)
        return package

    def load_cells(self, package=None):
        super(UpdateRow, self).load_cells(package)

        package = self.datum
        my_tenant_id = self.table.request.user.tenant_id
        pkg_categories = get_package_categories(package, my_tenant_id)
        for category in pkg_categories:
            self.classes.append('category-' + category)


class PackageDefinitionsTable(tables.DataTable):
    name = tables.Column('name', verbose_name=_('Package Name'))
    enabled = tables.Column('enabled', verbose_name=_('Active'))
    is_public = tables.Column('is_public', verbose_name=_('Public'))
    type = tables.Column('type', verbose_name=_('Type'))
    author = tables.Column('author', verbose_name=_('Author'))
    owner = tables.Column('owner_id',
                          verbose_name=_('Owner'),
                          hidden=True)

    def get_prev_pagination_string(self):
        pagination_string = super(
            PackageDefinitionsTable, self).get_prev_pagination_string()
        return pagination_string + "&sort_dir=desc"

    class Meta(object):
        name = 'packages'
        prev_pagination_param = 'marker'
        verbose_name = _('Package Definitions')
        template = 'common/_data_table.html'
        row_class = UpdateRow
        table_actions = (OwnerFilter,
                         ImportPackage,
                         ImportBundle,
                         ToggleEnabled,
                         TogglePublicEnabled,
                         DeletePackage)

        row_actions = (ModifyPackage,
                       DownloadPackage,
                       ToggleEnabled,
                       TogglePublicEnabled,
                       DeletePackage)
