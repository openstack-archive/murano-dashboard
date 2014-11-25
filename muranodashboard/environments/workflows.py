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

from django.core.urlresolvers import reverse
from django.core import validators
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import forms
from horizon import workflows

from muranodashboard.environments import api


LOG = logging.getLogger(__name__)
HELP_TEXT = _("Environment names must contain only alphanumeric or '_-.'"
              " characters and must start with alpha")


class SelectProjectUserAction(workflows.Action):
    project_id = forms.ChoiceField(label=_("Project"))
    user_id = forms.ChoiceField(label=_("User"))

    def __init__(self, request, *args, **kwargs):
        super(SelectProjectUserAction, self).__init__(request, *args, **kwargs)
        # Set our project choices
        projects = [(tenant.id, tenant.name)
                    for tenant in request.user.authorized_tenants]
        self.fields['project_id'].choices = projects

        # Set our user options
        users = [(request.user.id, request.user.username)]
        self.fields['user_id'].choices = users

    class Meta:
        name = _("Project & User")
        # Unusable permission so this is always hidden. However, we
        # keep this step in the workflow for validation/verification purposes.
        permissions = ("!",)


class SelectProjectUser(workflows.Step):
    action_class = SelectProjectUserAction


class ConfigureEnvironmentAction(workflows.Action):
    name = forms.CharField(
        label=_("Environment Name"),
        help_text=HELP_TEXT,
        required=True,
        validators=[validators.RegexValidator('^[a-zA-Z]+[\w-]*$')],
        error_messages={'invalid': HELP_TEXT})

    class Meta:
        name = _("Environment")
        help_text_template = "environments/_help.html"


class ConfigureEnvironment(workflows.Step):
    action_class = ConfigureEnvironmentAction
    contributes = ('name',)

    def contribute(self, data, context):
        if data:
            context['name'] = data.get('name', '')
        return context


class CreateEnvironment(workflows.Workflow):
    slug = "create"
    name = _("Create Environment")
    finalize_button_name = _("Create")
    success_message = _('Created environment "%s".')
    failure_message = _('Unable to create environment "%s".')
    default_steps = (SelectProjectUser, ConfigureEnvironment)

    def get_success_url(self):
        env_id = self.context.get('environment_id')
        return reverse("horizon:murano:environments:services", args=[env_id])

    def format_status_message(self, message):
        name = self.context.get('name', 'noname')
        return message % name

    def handle(self, request, context):
        try:
            environment = api.environment_create(request, context)
            context['environment_id'] = environment.id
            return True

        except Exception:
            name = self.context.get('name', 'noname')
            LOG.error("Unable to create environment {0}".format(name))
            exceptions.handle(request)
            return False


class UpdateEnvironmentInfoAction(workflows.Action):
    name = forms.CharField(
        label=_("Environment Name"),
        help_text=HELP_TEXT,
        required=True,
        validators=[validators.RegexValidator('^[a-zA-Z]+[\w-]*$')],
        error_messages={'invalid': HELP_TEXT})

    def handle(self, request, data):
        try:
            api.environment_update(request,
                                   data['environment_id'],
                                   data['name'])
        except Exception:
            exceptions.handle(request, ignore=True)
            LOG.error("Unable to update environment name with ud={0}".format(
                data['environment_id'],
            ))
            return False
        return True

    class Meta:
        name = _("Environment Info")
        slug = 'environment_info'
        help_text = _("Environment defines the run time context for the "
                      "application including all the application images, "
                      "automatically generated network configuration")


class UpdateEnvironmentInfo(workflows.Step):
    action_class = UpdateEnvironmentInfoAction
    depends_on = ('environment_id',)
    contributes = ('name',)

    def contribute(self, data, context):
        if data:
            context['name'] = data.get('name', '')
        return context


class UpdateEnvironment(workflows.Workflow):
    slug = "update_environment"
    name = _("Edit Environment")
    finalize_button_name = _("Save")
    success_message = _('Modified environment "%s".')
    failure_message = _('Unable to modify environment "%s".')
    success_url = "horizon:murano:environments:index"
    default_steps = (UpdateEnvironmentInfo,)

    def format_status_message(self, message):
        return message % self.context.get('name', 'unknown environment')
