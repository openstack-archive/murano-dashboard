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

WF_MANAGEMENT_NAME = 'workflowManagement'


class WorkflowManagementForm(object):
    def __init__(self):
        self.name = WF_MANAGEMENT_NAME
        self.field_specs = [
            {'name': 'stay_at_the_catalog',
             'initial': False,
             'description': 'If checked, you will be returned to the '
                            'Catalog page. If not - to the '
                            'Environment page, where you can deploy'
                            ' the application.',
             'required': False,
             'type': 'boolean',
             'label': 'Continue application adding'}]
        self.validators = []

    def name_field(self, fqn):
        return {'name': 'application_name',
                'type': 'string',
                'description': 'Enter a desired name for the application. '
                               'Just A-Z, a-z, 0-9, dash and underline'
                               ' are allowed',
                'label': 'Application Name',
                'regexpValidator': '^[-\w]+$',
                'initial': fqn.split('.')[-1]
                }
