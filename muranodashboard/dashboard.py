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

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
import horizon

# Load the api rest services into Horizon
import muranodashboard.api.rest  # noqa
from muranodashboard import exceptions
# prevent pyflakes from fail
assert exceptions


class DeployPanels(horizon.PanelGroup):
    slug = "deployment_group"
    name = _("Catalog")
    panels = ("environments", "catalog")


class ManagePanels(horizon.PanelGroup):
    slug = "manage_metadata"
    name = _("Manage")
    panels = ("images", "packages", "categories")


class Murano(horizon.Dashboard):
    name = getattr(settings, 'MURANO_DASHBOARD_NAME', _("Applications"))
    slug = "murano"
    panels = (DeployPanels, ManagePanels)
    default_panel = "environments"
    supports_tenants = True


horizon.register(Murano)
