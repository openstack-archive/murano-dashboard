#    Copyright (c) 2014 Mirantis, Inc.
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

from horizon import workflows


log = logging.getLogger(__name__)


class AddAppAction(workflows.Action):
    class Meta:
        name = _("Add Application")


class AddAppStep(workflows.Step):
    action_class = AddAppAction


class AddApplication(workflows.Workflow):
    slug = "add"
    name = _("Add Application")
    finalize_button_name = _("Add")
    success_message = _('Added application "%s".')
    failure_message = _('Unable to add application "%s".')
    success_url = "horizon:murano:catalog:index"
    default_steps = (AddAppStep, )
