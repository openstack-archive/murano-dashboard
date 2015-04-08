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

from django.core.urlresolvers import reverse_lazy


from horizon.forms import views
from horizon import tables as horizon_tables

from muranodashboard import api
from muranodashboard.categories import forms
from muranodashboard.categories import tables


class CategoriesView(horizon_tables.DataTableView):
    table_class = tables.CategoriesTable
    template_name = 'categories/index.html'

    def get_data(self):
        categories = []
        with api.handled_exceptions(self.request):
            categories = api.muranoclient(self.request).categories.list()
        return sorted(categories, key=lambda category: category.name)


class AddCategoryView(views.ModalFormView):
    form_class = forms.AddCategoryForm
    template_name = 'categories/add.html'
    context_object_name = 'category'
    success_url = reverse_lazy('horizon:murano:categories:index')
