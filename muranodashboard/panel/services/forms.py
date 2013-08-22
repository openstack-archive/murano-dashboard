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

import re
from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
import muranodashboard.panel.services.fields as fields
import muranodashboard.panel.services.helpers as helpers
import yaql


class UpdatableFieldsForm(forms.Form):
    def update_fields(self):
        # duplicate all password fields
        while True:
            index, inserted = 0, False
            for name, field in self.fields.iteritems():
                if isinstance(field, fields.PasswordField) and \
                        not field.has_clone:
                    self.fields.insert(index + 1,
                                       field.get_clone_name(name),
                                       field.clone_field())
                    inserted = True
                    break
                index += 1
            if not inserted:
                break

        for name, field in self.fields.iteritems():
            if hasattr(field, 'update'):
                field.update(self.initial)
            if not field.required:
                field.widget.attrs['placeholder'] = 'Optional'


class ServiceConfigurationForm(UpdatableFieldsForm):
    types = {
        'string': fields.CharField,
        'boolean': fields.BooleanField,
        'instance': fields.InstanceCountField,
        'clusterip': fields.ClusterIPField,
        'domain': fields.DomainChoiceField,
        'password': fields.PasswordField,
        'integer': fields.IntegerField,
        'databaselist': fields.DatabaseListField,
        'datagrid': fields.DataGridField,
        'flavor': fields.FlavorChoiceField,
        'image': fields.ImageChoiceField,
        'azone': fields.AZoneChoiceField,
        'text': (fields.CharField, forms.Textarea)
    }

    localizable_keys = set(['label', 'help_text', 'error_messages'])

    def __init__(self, *args, **kwargs):
        super(ServiceConfigurationForm, self).__init__(*args, **kwargs)
        self.attribute_mappings = {}
        self.insert_fields(self.fields_template)
        self.initial = kwargs.get('initial', self.initial)
        self.update_fields()

    @staticmethod
    def get_yaql_expr(expr):
        return type(expr) == dict and expr.get('YAQL', None)

    def init_attribute_mappings(self, field_name, kwargs):
        def set_mapping(name, value):
            """Spawns new dictionaries for each dot found in name."""
            bits = name.split('.')
            head, tail, mapping = bits[0], bits[1:], self.attribute_mappings
            while tail:
                if not head in mapping:
                    mapping[head] = {}
                head, tail, mapping = tail[0], tail[1:], mapping[head]
            mapping[head] = value

        if 'attribute_names' in kwargs:
            attr_names = kwargs['attribute_names']
            if type(attr_names) == list:
                # allow pushing field value to multiple attributes
                for attr_name in attr_names:
                    set_mapping(attr_name, field_name)
            elif attr_names:
                # if attributeNames = false, do not push field value
                set_mapping(attr_names, field_name)
            del kwargs['attribute_names']
        else:
            # default mapping: field to attr with same name
            # do not spawn new dictionaries for any dot in field_name
            self.attribute_mappings[field_name] = field_name

    def init_field_descriptions(self, kwargs):
        if 'description' in kwargs:
            del kwargs['description']
        if 'description_title' in kwargs:
            del kwargs['description_title']

    def insert_fields(self, field_specs):
        def process_widget(kwargs, cls, widget):
            widget = kwargs.get('widget', widget)
            if widget is None:
                widget = cls.widget
            if 'widget_media' in kwargs:
                media = kwargs['widget_media']
                del kwargs['widget_media']

                class Widget(widget):
                    class Media:
                        js = media.get('js', ())
                        css = media.get('css', {})
                widget = Widget
            if 'widget_attrs' in kwargs:
                widget = widget(attrs=kwargs['widget_attrs'])
                del kwargs['widget_attrs']
            return widget

        def append_field(field_spec):
            cls = parse_spec(field_spec['type'], 'type')[1]
            widget = None
            if type(cls) == tuple:
                cls, widget = cls
            kwargs = parse_spec(field_spec)[1]
            kwargs['widget'] = process_widget(kwargs, cls, widget)
            cls = cls.push_properties(kwargs)

            self.init_attribute_mappings(field_spec['name'], kwargs)
            self.init_field_descriptions(kwargs)
            self.fields.insert(len(self.fields),
                               field_spec['name'],
                               cls(**kwargs))

        def prepare_regexp(regexp):
            if regexp[0] == '/':
                groups = re.match(r'^/(.*)/([A-Za-z]*)$', regexp).groups()
                regexp, flags_str = groups
                flags = 0
                for flag in helpers.explode(flags_str):
                    flag = flag.upper()
                    if hasattr(re, flag):
                        flags |= getattr(re, flag)
                return RegexValidator(re.compile(regexp, flags))
            else:
                return RegexValidator(re.compile(regexp))

        def is_localizable(keys):
            return set(keys).intersection(self.localizable_keys)

        def make_property(key, spec):
            def _get(field):
                return self.get_data(spec)

            def _set(field, value):
                field.__dict__[key] = value

            def _del(field):
                del field.__dict__[key]
            return property(_get, _set, _del)

        def parse_spec(spec, keys=[]):
            if not type(keys) == list:
                keys = [keys]
            key = keys and keys[-1] or None
            if self.get_yaql_expr(spec):
                return key, make_property(key, spec)
            elif type(spec) == dict:
                items = []
                for k, v in spec.iteritems():
                    if not k in ('type', 'name'):
                        k = helpers.decamelize(k)
                        newKey, v = parse_spec(v, keys + [k])
                        if newKey:
                            k = newKey
                        items.append((k, v))
                return key, dict(items)
            elif type(spec) == list:
                return key, [parse_spec(_spec, keys)[1] for _spec in spec]
            elif type(spec) in (str, unicode) and is_localizable(keys):
                return key, _(spec)
            else:
                if key == 'type':
                    return key, self.types[spec]
                elif key == 'hidden' and spec is True:
                    return 'widget', forms.HiddenInput
                elif key == 'regexp_validator':
                    return 'validators', [prepare_regexp(spec)]
                else:
                    return key, spec

        for spec in field_specs:
            append_field(spec)

    def get_data(self, expr, data=None):
        """First try to get value from cleaned data, if none
        found, use raw data."""
        context = yaql.create_context()
        data = data or getattr(self, 'cleaned_data', None)
        expr = self.get_yaql_expr(expr)
        value = data and yaql.parse(expr).evaluate(data, context)
        # if value is None:
        #     name = self.add_prefix(spec[1:])
        #     value = self.data.get(name, None)
        return value

    def get_unit_templates(self, data):
        def parse_spec(spec):
            if type(spec) == list:
                return [parse_spec(_spec) for _spec in spec]
            elif type(spec) == dict:
                return dict(
                    (parse_spec(k), parse_spec(v))
                    for (k, v) in spec.iteritems())
            elif self.get_yaql_expr(spec):
                return self.get_data(spec, data)
            else:
                return spec
        return [parse_spec(spec) for spec in self.service.unit_templates]

    def extract_attributes(self, attributes):
        def get_data(name):
            if type(name) == dict:
                return dict((k, get_data(v)) for (k, v) in name.iteritems())
            else:
                return self.cleaned_data[name]
        for attr_name, field_name in self.attribute_mappings.iteritems():
            attributes[attr_name] = get_data(field_name)

    def clean(self):
        cleaned_data = super(ServiceConfigurationForm, self).clean()

        context = yaql.create_context()
        for validator in self.validators:
            expr = self.get_yaql_expr(validator['expr'])
            if not yaql.parse(expr).evaluate(cleaned_data, context):
                raise forms.ValidationError(_(validator.get('message', '')))

        for name, field in self.fields.iteritems():
            if isinstance(field, fields.PasswordField):
                field.compare(name, cleaned_data)

            if hasattr(field, 'postclean'):
                value = field.postclean(self, cleaned_data)
                if value:
                    cleaned_data[name] = value

        return cleaned_data
