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

from django.utils.translation import ugettext_lazy as _
from horizon import tabs

from muranodashboard.stats import models


class APIStatsTab(tabs.Tab):
    name = _("Murano API Servers")
    slug = "murano_srv"
    template_name = "stats/_api_srv.html"
    preload = False

    def get_context_data(self, request):
        stats = models.StatsModel().get_api_stats(request)
        return {'api_servers': stats}


class InstanceStatsTab(tabs.Tab):
    name = _("Murano Instance Statistics")
    slug = "murano_eng"
    template_name = "stats/_billing.html"
    preload = False

    def get_context_data(self, request):
        stm = models.BillingStats()
        stats = stm.get_all(request)
        context = {'stats': stats,
                   'grp_id': 'murano_billing',
                   'offset': ''}
        return context


class StatsTabs(tabs.TabGroup):
    slug = "stats_group"
    tabs = (InstanceStatsTab, APIStatsTab)
