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

import logging

from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import tables
from muranoclient.common import exceptions as exc

from muranodashboard import api

LOG = logging.getLogger(__name__)


class AddCategory(tables.LinkAction):
    name = "add_category"
    verbose_name = _("Add Category")
    url = "horizon:murano:categories:add"
    classes = ("ajax-modal",)
    icon = "plus"


class DeleteCategory(tables.DeleteAction):
    data_type_singular = _('Category')
    data_type_plural = _('Categories')

    def allowed(self, request, category=None):
        if category is not None:
            if not category.package_count:
                return True
        return False

    def delete(self, request, obj_id):
        try:
            api.muranoclient(request).categories.delete(obj_id)
        except exc.HTTPException:
            LOG.exception(_('Unable to delete category'))
            exceptions.handle(request,
                              _('Unable to remove package.'),
                              redirect='horizon:murano:categories:index')


class CategoriesTable(tables.DataTable):
    name = tables.Column('name', verbose_name=_('Category Name'))
    package_count = tables.Column('package_count',
                                  verbose_name=_('Package Count'))

    class Meta:
        name = 'categories'
        verbose_name = _('Application Categories')
        table_actions = (AddCategory,)
        row_actions = (DeleteCategory,)
        multi_select = False
