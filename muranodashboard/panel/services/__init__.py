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
from django.template.defaultfilters import slugify
from collections import OrderedDict
from yaml.scanner import ScannerError
import yaml
import re


_all_services = OrderedDict()


def import_all_services():
    from muranodashboard.panel.services.__common import decamelize
    directory = os.path.dirname(__file__)
    for fname in sorted(os.listdir(directory)):
        try:
            if fname.endswith('.yaml'):
                name = os.path.splitext(fname)[0]
                path = os.path.join(directory, fname)
                modified_on = os.stat(path).st_mtime
                if (not name in _all_services or
                        _all_services[name][0] < modified_on):
                    with open(path) as f:
                            kwargs = {decamelize(k): v
                                      for k, v in yaml.load(f).iteritems()}
                            _all_services[name] = (modified_on,
                                                   type(name, (), kwargs))
        except ScannerError:
            pass
        except OSError:
            pass


def iterate_over_services():
    import_all_services()
    for id, service_data in _all_services.items():
        modified_on, service_cls = service_data
        from muranodashboard.panel.services.__common import \
            ServiceConfigurationForm
        forms = []
        for fields in service_cls.forms:
            class Form(ServiceConfigurationForm):
                service = service_cls
                fields_template = fields
            forms.append(Form)
        yield slugify(service_cls.name), service_cls, forms


def iterate_over_service_forms():
    for slug, Service, forms in iterate_over_services():
        for step, form in zip(xrange(len(forms)), forms):
            yield '{0}-{1}'.format(slug, step), form


def with_service(slug, getter, default):
    import_all_services()
    match = re.match('(.*)-[0-9]+', slug)
    if match:
        slug = match.group(1)
    for _slug, Service, forms in iterate_over_services():
        if _slug == slug:
            return getter(Service)
    return default


def get_service_template(slug):
    return with_service(slug, lambda Service: Service.template, '')


def get_service_name(slug):
    return with_service(slug, lambda Service: Service.name, '')


def get_service_client(slug):
    return with_service(slug, lambda Service: Service.type, None)


def get_service_field_descriptions(slug, index):
    def get_descriptions(Service):
        form = Service.forms[index]
        descriptions = []
        for field in form:
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
    return [(slug, Service.name) for slug, Service, forms in
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
    return [(slug, Service.description) for slug, Service, forms in
            iterate_over_services()]
