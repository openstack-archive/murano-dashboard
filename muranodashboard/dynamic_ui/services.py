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

import os
import re
import semantic_version

from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from oslo_log import log as logging
import six
from yaql import legacy

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


class Service(object):
    """Murano Service representation object

    Class for keeping service persistent data, the most important are two:
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
    def __init__(self, cleaned_data, version, fqn, forms=None, templates=None,
                 application=None, parameters=None, **kwargs):
        self.cleaned_data = cleaned_data
        self.templates = templates or {}
        self.spec_version = str(version)
        if forms is None:
            forms = []

        if application is None:
            raise ValueError('Application section is required')
        else:
            self.application = application

        self.context = legacy.create_context()
        self.context['?service'] = self
        yaql_functions.register(self.context)

        params = parameters or {}
        self.parameters = {}
        for k, v in six.iteritems(params):
            if not k or not k[0].isalpha():
                continue
            v = helpers.evaluate(v, self.context)
            self.parameters[k] = v
            self.context[k] = v

        self.forms = []
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

        for form in forms:
            (name, field_specs, validators,
             region) = self.extract_form_data(form)
            # NOTE(kzaitsev) should be str (not unicode) under python2
            # however it also works as str under python3
            name = helpers.to_str(name)
            self._add_form(name, field_specs, validators, region)

        # Add ManageWorkflowForm
        workflow_form = catalog_forms.WorkflowManagementForm()
        if semantic_version.Version.coerce(self.spec_version) >= \
                semantic_version.Version.coerce('2.2'):
            app_name_field = workflow_form.name_field(fqn)
            workflow_form.field_specs.insert(0, app_name_field)

        self._add_form(workflow_form.name,
                       workflow_form.field_specs,
                       workflow_form.validators)

    def _add_form(self, _name, _specs, _validators, _verbose_name=None,
                  _region=None):
        import muranodashboard.dynamic_ui.forms as forms

        class Form(six.with_metaclass(forms.DynamicFormMetaclass,
                   forms.ServiceConfigurationForm)):
            service = self
            name = _name
            verbose_name = _verbose_name
            field_specs = _specs
            validators = _validators
            region = _region

        self.forms.append(Form)

    @staticmethod
    def extract_form_data(data):
        for form_name, form_data in six.iteritems(data):
            return (form_name, form_data['fields'],
                    form_data.get('validators', []), form_data.get('region'))

    def extract_attributes(self):
        context = self.context.create_child_context()
        context['$'] = self.cleaned_data
        context['$forms'] = self.cleaned_data

        for name, template in six.iteritems(self.templates):
            context[name] = template
        if semantic_version.Version.coerce(self.spec_version) \
                >= semantic_version.Version.coerce('2.2'):
            management_form = catalog_forms.WF_MANAGEMENT_NAME
            name = self.cleaned_data[management_form]['application_name']
            self.application['?']['name'] = name
        attributes = helpers.evaluate(self.application, context)
        return attributes

    def get_data(self, form_name, expr, data=None):
        """Try to get value from cleaned data, if none found, use raw data."""
        if data:
            self.update_cleaned_data(data, form_name=form_name)
        data = self.cleaned_data
        return expr.evaluate(data=data, context=self.context)

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
    app_version = ui_desc.pop('Version', version.LATEST_FORMAT_VERSION)
    version.check_version(app_version)
    service = dict(
        (helpers.decamelize(k), v) for (k, v) in six.iteritems(ui_desc))
    parameters = service.pop('parameters', {})
    parameters_source = service.pop('parameters_source', None)
    if parameters_source is not None:
        parts = parameters_source.rsplit('.', 1)
        if 2 >= len(parts) > 0:
            if len(parts) == 2:
                class_name, method_name = parts
            else:
                method_name = parts[0]
                class_name = service.get('application', {}).get('?', {}).get(
                    'type', fqn)

            details = pkg_api.get_package_details(request, app_id)
            pkg_version = getattr(details, 'version', '*')
            request_body = {
                'className': class_name,
                'methodName': method_name,
                'packageName': fqn,
                'classVersion': pkg_version,
                'parameters': {}
            }

            result = api.muranoclient(request).static_actions.call(
                request_body).get_result()
            if result and isinstance(result, dict):
                parameters.update(result)

    return Service(app_data, app_version, fqn, parameters=parameters,
                   **service)


def condition_getter(request, kwargs):
    """Define wizard conditional dictionary.

    This function generates conditional dictionary for application creation
       wizard. The last form of the wizard may be a management form, that
       is provided by murano, not by a user. But in some cases this field
       should be hidden. So here all situations are proceeded.
       Management form may contain the following fields:
       * continue adding applications chechkbox
         Hidden, when user adds an app from 'quick deploy' and from
        the other form (while creating depending app with '+' sign
       * automatic inserted name
         Hidden, if app version not higher then 2.0

       So if both fields should not be shown - the management form is hidden.
    """
    def _func(wizard):
        # Get last key in OrderDict
        last_step = next(reversed(wizard.form_list))
        app_spec_version = wizard.form_list[last_step].service.spec_version
        hide_stay_at_catalog_dialog = wizard.get_wizard_flag('drop_wm_form')
        # Hide management form if version is old and additional dialog should
        # not be shown
        if not semantic_version.Version.coerce(app_spec_version) >= \
                semantic_version.Version.coerce('2.2')\
                and hide_stay_at_catalog_dialog:
            return False
        last_form_fields = wizard.form_list[last_step].base_fields
        # If version is old, do not ask for app name
        if not semantic_version.Version.coerce(app_spec_version) >= \
                semantic_version.Version.coerce('2.2'):
            if 'application_name' in last_form_fields.keys():
                del last_form_fields['application_name']
        # If workflow checkbox is not needed, remove it
        if hide_stay_at_catalog_dialog:
            if 'stay_at_the_catalog' in last_form_fields.keys():
                del last_form_fields['stay_at_the_catalog']
        return True

    app = import_app(request, kwargs['app_id'])
    key = force_text(_get_form_name(len(app.forms) - 1, app.forms[-1]()))

    return {key: _func}


def _get_form_name(i, form, step_tmpl='Step {0}'):
    name = form.verbose_name
    return step_tmpl.format(i + 1) if name is None else name


def get_app_forms(request, kwargs):
    app = import_app(request, kwargs.get('app_id'))

    def get_form_name(i, form):
        return _get_form_name(i, form, _('Step {0}'))

    step_names = [get_form_name(*pair) for pair in enumerate(app.forms)]
    return list(zip(step_names, app.forms))


def service_type_from_id(service_id):
    match = re.match('(.*)-[0-9]+', service_id)
    if match:
        return match.group(1)
    else:  # if no number suffix found, it was service_type itself passed in
        return service_id


def get_app_field_descriptions(request, app_id, index):
    app = import_app(request, app_id)

    form_cls = app.forms[index]
    descriptions = []
    no_field_descriptions = []
    for name, field in six.iteritems(form_cls.base_fields):
        title = field.description_title
        description = field.description
        if description:
            if field.widget.is_hidden:
                no_field_descriptions.extend([description, title])
            else:
                descriptions.append((name, title, description))
    return descriptions, no_field_descriptions
