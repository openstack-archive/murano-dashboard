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

from django.conf import settings
from django.template.defaultfilters import slugify
from ordereddict import OrderedDict

import yaml
from yaml.scanner import ScannerError


_all_services = OrderedDict()


class Service(object):
    def __init__(self, modified_on, **kwargs):
        import muranodashboard.panel.services.forms as services
        for key, value in kwargs.iteritems():
            if key == 'forms':
                self.forms = []
                for form_data in value:
                    form_name, form_data = self.extract_form_data(form_data)
                    self.forms.append(
                        type(form_name, (services.ServiceConfigurationForm,),
                             {'service': self,
                              'fields_template': form_data['fields'],
                              'validators': form_data.get('validators', [])}))
            else:
                setattr(self, key, value)
        self.modified_on = modified_on
        self.cleaned_data = {}

    @staticmethod
    def extract_form_data(form_data):
        form_name = form_data.keys()[0]
        return form_name, form_data[form_name]

    def update_cleaned_data(self, form, data):
        if data:
            # match = re.match('^.*-(\d)+$', form.prefix)
            # index = int(match.group(1)) if match else None
            # if index is not None:
            #     self.cleaned_data[index] = data
            self.cleaned_data[form.__class__.__name__] = data
        return self.cleaned_data


def import_all_services():
    from muranodashboard.panel.services.helpers import decamelize

    directory = getattr(settings, 'MURANO_SERVICES_DESC_PATH', None)
    if directory is None:
        directory = os.path.join(os.path.dirname(__file__), '../../services/')

    for filename in os.listdir(directory):
        if not filename.endswith('.yaml'):
            continue

        service_file = os.path.join(directory, filename)
        modified_on = os.path.getmtime(service_file)

        if filename in _all_services:
            if _all_services[filename].modified_on >= modified_on:
                continue

        try:
            with open(service_file) as stream:
                yaml_desc = yaml.load(stream)
        except (OSError, ScannerError):
            continue

        service = dict((decamelize(k), v) for (k, v) in yaml_desc.iteritems())
        _all_services[filename] = Service(modified_on, **service)


def iterate_over_services():
    import_all_services()

    for service in sorted(_all_services.values(), key=lambda v: v.name):
        yield slugify(service.name), service, service.forms


def iterate_over_service_forms():
    for slug, service, forms in iterate_over_services():
        for step, form in enumerate(forms):
            yield '{0}-{1}'.format(slug, step), form


def with_service(slug, getter, default):
    import_all_services()
    match = re.match('(.*)-[0-9]+', slug)
    if match:
        slug = match.group(1)
    for _slug, service, forms in iterate_over_services():
        if _slug == slug:
            return getter(service)
    return default


def get_service_name(slug):
    return with_service(slug, lambda service: service.name, '')


def get_service_client(slug):
    return with_service(slug, lambda service: service.type, None)


def get_service_field_descriptions(slug, index):
    def get_descriptions(service):
        Form = service.forms[index]
        descriptions = []
        for field in Form.fields_template:
            if 'description' in field:
                title = field.get('descriptionTitle', field.get('label', ''))
                descriptions.append((title, field['description']))
        return descriptions
    return with_service(slug, get_descriptions, [])


def get_service_type(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step('service_choice') \
        or {'service': 'none'}
    return cleaned_data.get('service')


def get_service_choices():
    return [(slug, service.name) for slug, service, forms in
            iterate_over_services()]


def get_service_checkers():
    import_all_services()

    def make_comparator(slug):
        def compare(wizard):
            match = re.match('(.*)-[0-9]+', slug)
            return match and match.group(1) == get_service_type(wizard)
        return compare

    return [(slug, make_comparator(slug)) for slug, form
            in iterate_over_service_forms()]


def get_service_descriptions():
    return [(slug, service.description) for slug, service, forms in
            iterate_over_services()]
