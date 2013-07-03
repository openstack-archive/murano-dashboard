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
from django.utils.datastructures import SortedDict
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

        detail_info = SortedDict([
            ('Name', service_data.name),
            ('Type', service_data.service_type),
            ('Status', status_name),
            ('Hostname', service_data.units[0].state.hostname), ])

        if not service_data.domain:
            detail_info['Domain'] = 'Not in domain'

        if hasattr(service_data, 'uri'):
            detail_info['URI'] = service_data.uri

        return {'service': detail_info}


class LogsTab(tabs.Tab):
    name = _("Logs")
    slug = "_logs"
    template_name = '_service_logs.html'
    preload = False

    def get_context_data(self, request):
        service_id = self.tab_group.kwargs['service_id']
        environment_id = self.tab_group.kwargs['environment_id']
        reports = api.get_status_messages_for_service(request, service_id,
                                                      environment_id)
        return {"reports": reports}


class ServicesTabs(tabs.TabGroup):
    slug = "services_details"
    tabs = (OverviewTab, LogsTab)
    sticky = True
