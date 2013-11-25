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
from django.forms import MediaDefiningClass
from .utils import Action, CheckboxInput, FILE_STEPS
from horizon import exceptions
from horizon import forms
from horizon import workflows

from muranodashboard.environments.services.metadata import metadataclient

log = logging.getLogger(__name__)


class EditManifest(Action):
    service_display_name = forms.CharField(label=_('Service Name'),
                                           required=True)
    full_service_name = forms.CharField(
        label=_('Fully Qualified Service Name'), required=True)
    version = forms.CharField(label=_('Version'), initial='1')
    enabled = forms.BooleanField(label=_('Active'), initial=True,
                                 widget=CheckboxInput)
    description = forms.CharField(label=_('Description'),
                                  widget=forms.Textarea)

    def __init__(self, request, context, *args, **kwargs):
        super(EditManifest, self).__init__(request, context, *args, **kwargs)
        # disable field with service_id for service being modified
        if context and context.get('full_service_name'):
            self.fields['full_service_name'].widget.attrs.update({
                'disabled': True
            })

    class Meta:
        name = _('Manifest')
        help_text_template = "service_catalog/_help_manifest.html"


class EditManifestStep(workflows.Step):
    __metaclass__ = MediaDefiningClass
    action_class = EditManifest
    template_name = 'service_catalog/_workflow_step.html'
    contributes = ('service_display_name', 'full_service_name',
                   'version', 'enabled', 'description')

    # Workflow doesn't handle Media inner class of widgets for us, so we need
    # to inject media directly to the step
    class Media:
        css = {'all': ('muranodashboard/css/checkbox.css',)}
        js = ('muranodashboard/js/submit-disabled.js',)


class ComposeService(workflows.Workflow):
    slug = "compose_service"
    name = _("Compose Service")
    finalize_button_name = _("Submit")
    success_message = _('Service "%s" created.')
    failure_message = _('Unable to create service "%s".')
    modify_success_message = _('Service "%s" modified.')
    modify_failure_message = _('Unable to modify service "%s".')
    success_url = "horizon:murano:service_catalog:index"
    default_steps = (EditManifestStep,) + tuple(FILE_STEPS)

    def __init__(self, request=None, context_seed=None, *args, **kwargs):
        if context_seed and context_seed.get('full_service_name'):
            self.success_message = self.modify_success_message
            self.failure_message = self.modify_failure_message
        super(ComposeService, self).__init__(
            request, context_seed, *args, **kwargs)

    def format_status_message(self, message):
        name = self.context.get('service_display_name', 'noname')
        return message % name

    def handle(self, request, context):
        try:
            return metadataclient(request).metadata_admin.create_service(
                context.get('full_service_name'), context)
        except Exception:
            name = self.context.get('service_display_name', 'noname')
            log.error("Unable to create/modify service {0}".format(name))
            exceptions.handle(request)
            return False
