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
import types

from django import forms
from django.utils.translation import ugettext_lazy as _
import muranodashboard.dynamic_ui.fields as fields
import muranodashboard.dynamic_ui.helpers as helpers
import yaql


log = logging.getLogger(__name__)

TYPES = {
    'string': fields.CharField,
    'boolean': fields.BooleanField,
    'instance': fields.InstanceCountField,
    'clusterip': fields.ClusterIPField,
    'domain': fields.DomainChoiceField,
    'password': fields.PasswordField,
    'integer': fields.IntegerField,
    'databaselist': fields.DatabaseListField,
    'table': fields.TableField,
    'flavor': fields.FlavorChoiceField,
    'keypair': fields.KeyPairChoiceField,
    'image': fields.ImageChoiceField,
    'azone': fields.AZoneChoiceField,
    'text': (fields.CharField, forms.Textarea)
}


def _collect_fields(field_specs, form_name, service):
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

    def parse_spec(spec, keys=None):
        if keys is None:
            keys = []

        if not isinstance(keys, types.ListType):
            keys = [keys]
        key = keys and keys[-1] or None
        if helpers.get_yaql_expr(spec):
            return key, fields.RawProperty(key, spec)
        elif isinstance(spec, types.DictType):
            items = []
            for k, v in spec.iteritems():
                if not k in ('type', 'name'):
                    k = helpers.decamelize(k)
                    new_key, v = parse_spec(v, keys + [k])
                    if new_key:
                        k = new_key
                    items.append((k, v))
            return key, dict(items)
        elif isinstance(spec, types.ListType):
            return key, [parse_spec(_spec, keys)[1] for _spec in spec]
        elif isinstance(spec, basestring) and helpers.is_localizable(keys):
            return key, _(spec)
        else:
            if key == 'type':
                return key, TYPES[spec]
            elif key == 'hidden' and spec is True:
                return 'widget', forms.HiddenInput
            elif key == 'regexp_validator':
                return 'validators', [helpers.prepare_regexp(spec)]
            else:
                return key, spec

    def make_field(field_spec, form_name, service):
        cls = parse_spec(field_spec['type'], 'type')[1]
        widget = None
        if isinstance(cls, types.TupleType):
            cls, widget = cls
        kwargs = parse_spec(field_spec)[1]
        kwargs['widget'] = process_widget(kwargs, cls, widget)
        cls = cls.finalize_properties(kwargs, form_name, service)

        attribute_names = kwargs.pop('attribute_names', None)
        field = cls(**kwargs)
        field.attribute_names = attribute_names

        return field_spec['name'], field

    return [make_field(spec, form_name, service) for spec in field_specs]


class DynamicFormMetaclass(forms.forms.DeclarativeFieldsMetaclass):
    def __new__(meta, name, bases, dct):
        name = dct.pop('name', name)
        field_specs = dct.pop('field_specs', [])
        service = dct['service']
        for field_name, field in _collect_fields(field_specs, name, service):
            dct[field_name] = field
        return super(DynamicFormMetaclass, meta).__new__(
            meta, name, bases, dct)


class UpdatableFieldsForm(forms.Form):
    """This class is supposed to be a base for forms belonging to a FormWizard
    descendant, or be used as a mixin for workflows.Action class.

    In first case the `request' used in `update' method is provided in
    `self.initial' dictionary, in the second case request should be provided
    directly in `request' parameter.
    """
    def update_fields(self, request=None):
        # Create 'Confirm Password' fields by duplicating password fields
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
                field.update(self.initial, form=self, request=request)
            if not field.required:
                field.widget.attrs['placeholder'] = 'Optional'


class ServiceConfigurationForm(UpdatableFieldsForm):
    def __init__(self, *args, **kwargs):
        log.info("Creating form {0}".format(self.__class__.__name__))
        super(ServiceConfigurationForm, self).__init__(*args, **kwargs)
        self.attribute_mappings = {}
        self.context = helpers.create_yaql_context()
        self.finalize_fields()
        self.initial = kwargs.get('initial', self.initial)
        self.update_fields()

    def finalize_fields(self):
        for field_name, field in self.fields.iteritems():
            field.form = self

            validators = []
            for v in field.validators:
                expr = isinstance(v, types.DictType) and v.get('expr')
                if expr and isinstance(expr, fields.RawProperty):
                    v = fields.make_yaql_validator(field, self, field_name, v)
                validators.append(v)
            field.validators = validators

            self.init_attribute_mapping(field_name, field)

    def init_attribute_mapping(self, field_name, field):
        def set_mapping(name, value):
            """Spawns new dictionaries for each dot found in name."""
            bits = name.split('.')
            head, tail, mapping = bits[0], bits[1:], self.attribute_mappings
            while tail:
                if not head in mapping:
                    mapping[head] = {}
                head, tail, mapping = tail[0], tail[1:], mapping[head]
            mapping[head] = value

        attr_names = field.attribute_names
        if attr_names is not None:
            if isinstance(attr_names, types.ListType):
                # allow pushing field value to multiple attributes
                for attr_name in attr_names:
                    set_mapping(attr_name, field_name)
            elif attr_names:
                # if attributeNames = false, do not push field value
                set_mapping(attr_names, field_name)
        else:
            # default mapping: field to attr with same name
            # do not spawn new dictionaries for any dot in field_name
            self.attribute_mappings[field_name] = field_name
        del field.attribute_names

    def get_unit_templates(self, data):
        def parse_spec(spec):
            if helpers.get_yaql_expr(spec):
                data_ready, value = self.service.get_data(
                    self.__class__.__name__, spec, data)
                return value
            elif isinstance(spec, types.ListType):
                return [parse_spec(_spec) for _spec in spec]
            elif isinstance(spec, types.DictType):
                return dict(
                    (parse_spec(k), parse_spec(v))
                    for (k, v) in spec.iteritems())
            else:
                return spec
        unit_templates = getattr(self.service, 'unit_templates', [])
        return [parse_spec(spec) for spec in unit_templates]

    def extract_attributes(self, attributes):
        def get_attr(name):
            if isinstance(name, types.DictType):
                return dict((k, get_attr(v)) for (k, v) in name.iteritems())
            else:
                return self.cleaned_data[name]
        for attr_name, field_name in self.attribute_mappings.iteritems():
            attributes[attr_name] = get_attr(field_name)

    def clean(self):
        if self._errors:
            return self.cleaned_data
        else:
            cleaned_data = super(ServiceConfigurationForm, self).clean()
            all_data = self.service.update_cleaned_data(
                cleaned_data, form=self)
            error_messages = []
            for validator in self.validators:
                expr = helpers.get_yaql_expr(validator['expr'])
                if not yaql.parse(expr).evaluate(all_data, self.context):
                    error_messages.append(_(validator.get('message', '')))
            if error_messages:
                raise forms.ValidationError(error_messages)

            for name, field in self.fields.iteritems():
                if (isinstance(field, fields.PasswordField) and
                        getattr(field, 'enabled', True)):
                    field.compare(name, cleaned_data)

                if hasattr(field, 'postclean'):
                    value = field.postclean(self, cleaned_data)
                    if value:
                        cleaned_data[name] = value
                        log.debug("Update cleaned data in postclean method")

            self.service.update_cleaned_data(cleaned_data, form=self)
            return cleaned_data
