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
import os
import re
import yaql

from muranodashboard import api
from muranodashboard.api import packages as pkg_api
from muranodashboard.catalog import forms as catalog_forms
from muranodashboard.dynamic_ui import helpers
from muranodashboard.dynamic_ui import version
from muranodashboard.dynamic_ui import yaql_functions
from muranodashboard.environments import consts

LOG = logging.getLogger(__name__)


if not os.path.exists(consts.CACHE_DIR):
    os.mkdir(consts.CACHE_DIR)
    LOG.info('Creating cache directory located at {dir}'.format(
        dir=consts.CACHE_DIR))
LOG.info('Using cache directory located at {dir}'.format(
    dir=consts.CACHE_DIR))


_apps = {}


class Service(object):
    """Class for keeping service persistent data, the most important are two:
    ``self.forms`` list of service's steps (as Django form classes) and
    ``self.cleaned_data`` dictionary of data from service validated steps.

    Attribute ``self.cleaned_data`` is needed for, e.g. ServiceA.Step2, be
    able to reference data at ServiceA.Step1 while actual form instance
    representing Step1 is already gone. That attribute is stored per-user,
    so sessions are employed - the reference to a dictionary with forms data
    stored in a session is passed to Service during its initialization,
    because Service instance is re-created on each request from UI definition
    stored at local file-system cache .
    """
    def __init__(self, cleaned_data, forms=None, templates=None,
                 application=None, **kwargs):
        self.cleaned_data = cleaned_data
        self.templates = templates or {}

        if application is None:
            raise ValueError('Application section is required')
        else:
            self.application = application

        self.context = yaql.create_context()
        yaql_functions.register(self.context)

        self.forms = []
        for key, value in kwargs.iteritems():
            setattr(self, key, value)

        if forms:
            for data in forms:
                name, field_specs, validators = self.extract_form_data(data)
                self._add_form(name, field_specs, validators)

        # Add ManageWorkflowForm
        workflow_form = catalog_forms.WorkflowManagementForm
        self._add_form(workflow_form.name, workflow_form.field_specs,
                       workflow_form.validators)

    def _add_form(self, _name, _specs, _validators):
        import muranodashboard.dynamic_ui.forms as forms

        class Form(forms.ServiceConfigurationForm):
            __metaclass__ = forms.DynamicFormMetaclass

            service = self
            name = _name
            field_specs = _specs
            validators = _validators

        self.forms.append(Form)

    @staticmethod
    def extract_form_data(form_data):
        form_name = form_data.keys()[0]
        form_data = form_data[form_name]
        return form_name, form_data['fields'], form_data.get('validators', [])

    def extract_attributes(self):
        self.context.set_data(self.cleaned_data)
        for name, template in self.templates.iteritems():
            self.context.set_data(template, name)

        return helpers.evaluate(self.application, self.context)

    def get_data(self, form_name, expr, data=None):
        """First try to get value from cleaned data, if none
        found, use raw data.
        """
        if data:
            self.update_cleaned_data(data, form_name=form_name)
        data = self.cleaned_data
        value = data and expr.evaluate(data=data, context=self.context)
        return data != {}, value

    def update_cleaned_data(self, data, form=None, form_name=None):
        form_name = form_name or form.__class__.__name__
        if data:
            self.cleaned_data[form_name] = data
        return self.cleaned_data

    def set_data(self, data):
        self.cleaned_data = data


def get_apps_data(request):
    return request.session.setdefault('apps_data', {})


def import_app(request, app_id):
    app_data = get_apps_data(request).setdefault(app_id, {})

    ui_desc = pkg_api.get_app_ui(request, app_id)
    fqn = pkg_api.get_app_fqn(request, app_id)
    LOG.debug('Using data {0} for app {1}'.format(app_data, fqn))
    version.check_version(ui_desc.pop('Version', 1))
    service = dict(
        (helpers.decamelize(k), v) for (k, v) in ui_desc.iteritems())

    global _apps  # In-memory caching of dynamic UI forms
    if app_id in _apps:
        LOG.debug('Using in-memory forms for app {0}'.format(fqn))
        app = _apps[app_id]
        app.set_data(app_data)
    else:
        LOG.debug('Creating new forms for app {0}'.format(fqn))
        app = _apps[app_id] = Service(app_data, **service)
    return app


def condition_getter(request, kwargs):
    def _func(wizard):
        return not wizard.get_wizard_flag('drop_wm_form')

    app = import_app(request, kwargs['app_id'])
    last_form_key = str(len(app.forms) - 1)
    return {last_form_key: _func}


def get_app_forms(request, kwargs):
    app = import_app(request, kwargs.get('app_id'))
    return app.forms


def service_type_from_id(service_id):
    match = re.match('(.*)-[0-9]+', service_id)
    if match:
        return match.group(1)
    else:  # if no number suffix found, it was service_type itself passed in
        return service_id


def get_service_name(request, app_id):
    package = api.muranoclient(request).packages.get(app_id)
    return package.name


def get_app_field_descriptions(request, app_id, index):
    app = import_app(request, app_id)

    form_cls = app.forms[index]
    descriptions = []
    for name, field in form_cls.base_fields.iteritems():
        title = field.description_title
        description = field.description
        if description:
            descriptions.append((name, title, description))
    return descriptions
