#    Copyright (c) 2015 Mirantis, Inc.
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

from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
from horizon import exceptions
from horizon import tables
from muranoclient.common import exceptions as exc
from openstack_dashboard import policy
from oslo_log import log as logging

from muranodashboard import api
from muranodashboard.common import utils as md_utils

LOG = logging.getLogger(__name__)


class AddCategory(tables.LinkAction):
    name = "add_category"
    verbose_name = _("Add Category")
    url = "horizon:app-catalog:categories:add"
    classes = ("ajax-modal",)
    icon = "plus"
    policy_rules = (("murano", "add_category"),)


class DeleteCategory(policy.PolicyTargetMixin, tables.DeleteAction):
    policy_rules = (("murano", "delete_category"),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Category",
            u"Delete Categories",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Category",
            u"Deleted Categories",
            count
        )

    def allowed(self, request, category=None):
        use_artifacts = getattr(settings, 'MURANO_USE_GLARE', False)
        if use_artifacts:
            return category is not None
        if category is not None:
            if not category.package_count:
                return True
        return False

    def delete(self, request, obj_id):
        try:
            api.muranoclient(request).categories.delete(obj_id)
        except exc.HTTPException:
            msg = _('Unable to delete category')
            LOG.exception(msg)
            url = reverse('horizon:app-catalog:categories:index')
            exceptions.handle(request, msg, redirect=url)


class CategoriesTable(tables.DataTable):
    name = md_utils.Column('name', verbose_name=_('Category Name'))
    use_artifacts = getattr(settings, 'MURANO_USE_GLARE', False)
    if not use_artifacts:
        package_count = tables.Column('package_count',
                                      verbose_name=_('Package Count'))

    class Meta(object):
        name = 'categories'
        verbose_name = _('Application Categories')
        table_actions = (AddCategory,)
        row_actions = (DeleteCategory,)
        multi_select = False
