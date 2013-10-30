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

from django.utils.translation import ugettext as _

from horizon import exceptions
from horizon import forms
from horizon import workflows

from muranodashboard.environments import api


log = logging.getLogger(__name__)


class EditManifest(workflows.Action):
    service_display_name = forms.CharField(label=_('Service Name'),
                                           required=True)
    full_service_name = forms.CharField(
        label=_('Fullly Qualified Service Name'), required=True)
    version = forms.IntegerField(label=_('Version'), initial=1)
    enabled = forms.BooleanField(label=_('Active'), initial=True)
    description = forms.CharField(label=_('Description'),
                                  widget=forms.Textarea)

    class Meta:
        name = _('Manifest')
        #help_text_template = "environments/_help.html"


class EditManifestStep(workflows.Step):
    action_class = EditManifest
    contributes = ('service_display_name', 'full_service_name',
                   'version', 'enabled', 'description')

    def contribute(self, data, context):
        context.update(data)
        return context


class ComposeService(workflows.Workflow):
    slug = "compose_service"
    name = _("Compose Service")
    finalize_button_name = _("Submit")
    success_message = _('Service "%s" created.')
    failure_message = _('Unable to create service "%s".')
    success_url = "horizon:murano:service_catalog:index"
    default_steps = (EditManifestStep,)

    def format_status_message(self, message):
        name = self.context.get('name', 'noname')
        return message % name

    def handle(self, request, context):
        try:
            api.environment_create(request, context)
            return True
        except Exception:
            name = self.context.get('name', 'noname')
            log.error("Unable to create service {0}".format(name))
            exceptions.handle(request)
            return False
