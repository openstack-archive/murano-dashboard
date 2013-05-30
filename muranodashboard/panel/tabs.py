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

import logging

from django.utils.translation import ugettext_lazy as _
from horizon import tabs
from muranodashboard.panel import api
from muranodashboard.panel.tables import STATUS_DISPLAY_CHOICES


LOG = logging.getLogger(__name__)


class OverviewTab(tabs.Tab):
    name = _("Service")
    slug = "_service"
    template_name = '_services.html'

    def get_context_data(self, request):
        service_data = self.tab_group.kwargs['service']

        for id, name in STATUS_DISPLAY_CHOICES:
            if id == service_data.status:
                status_name = name

        detail_info = {"service_name": service_data.name,
                       "service_status": status_name,
                       "service_type": service_data.service_type,
                       "service_domain": service_data.domain}

        # service_data is a bunch obj
        if hasattr(service_data, 'loadBalancerIP'):
            detail_info["loadBalancerIP"] = service_data.loadBalancerIP

        return detail_info


class LogsTab(tabs.Tab):
    name = _("Logs")
    slug = "_logs"
    template_name = '_service_logs.html'

    def get_context_data(self, request):
        service = self.tab_group.kwargs['service']
        reports = api.get_status_message_for_service(request, service.id)
        return {"reports": reports}


class ServicesTabs(tabs.TabGroup):
    slug = "services_details"
    tabs = (OverviewTab, LogsTab)
    sticky = True
