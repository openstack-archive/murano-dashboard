#    Copyright (c) 2014 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the 'License'); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from horizon import tabs
import logging

from django.utils.translation import ugettext_lazy as _


LOG = logging.getLogger(__name__)


class AppOverviewTab(tabs.Tab):
    name = _('Overview')
    slug = 'app_overview'
    template_name = 'catalog/_overview.html'
    preload = False

    def __init__(self, *args, **kwargs):
        super(AppOverviewTab, self).__init__(*args, **kwargs)
        self.app = self.tab_group.kwargs['application']
        LOG.debug('AppOverviewTab: {0}'.format(self.app))

    def get_context_data(self, request):
        return {'app': self.app}


class AppRequirementsTab(tabs.Tab):
    name = _('Requirements')
    slug = 'app_requirements'
    template_name = 'catalog/_app_requirements.html'
    preload = False

    def __init__(self, *args, **kwargs):
        super(AppRequirementsTab, self).__init__(*args, **kwargs)
        self.app = self.tab_group.kwargs['application']
        LOG.debug('AppREquirementsTab: {0}'.format(self.app))

    def get_context_data(self, request):
        return {'application': self.app}


class AppLicenseAgreementTab(tabs.Tab):
    name = _('License')
    slug = 'app_license'
    template_name = 'catalog/_app_license.html'
    preload = False

    def __init__(self, *args, **kwargs):
        super(AppLicenseAgreementTab, self).__init__(*args, **kwargs)
        self.app = self.tab_group.kwargs['application']
        LOG.debug('AppLicenseAgreementTab: {0}'.format(self.app))

    def get_context_data(self, request):
        return {'application': self.app}


class ApplicationTabs(tabs.TabGroup):
    slug = 'app_details'
    tabs = (AppOverviewTab, AppRequirementsTab, AppLicenseAgreementTab)

    def __init__(self, *args, **kwargs):
        self.app = kwargs.get('application', None)
        LOG.debug('ApplicationTabs: {0}'.format(self.app))
        super(ApplicationTabs, self).__init__(*args, **kwargs)
