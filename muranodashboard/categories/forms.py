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

from django import forms
from django.utils.translation import ugettext_lazy as _
from horizon import forms as horizon_forms
from horizon import messages

from muranodashboard import api


class AddCategoryForm(horizon_forms.SelfHandlingForm):

    name = forms.CharField(label=_('Category Name'),
                           max_length=80,
                           help_text=_('80 characters max.'))

    def handle(self, request, data):
        if data:
            with api.handled_exceptions(self.request):
                category = api.muranoclient(self.request).categories.add(data)
                messages.success(request, _('Category {0} created.')
                                 .format(data['name']))
                return category
