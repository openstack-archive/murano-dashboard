import re
import ast
import json
from django import forms
from django.core.validators import RegexValidator, validate_ipv4_address
from netaddr import all_matching_cidrs
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_text
from muranodashboard.panel import api
from horizon import exceptions, messages
from openstack_dashboard.api import glance
from openstack_dashboard.api.nova import novaclient
from muranodashboard.datagrids import DataGridCompound
import copy
from django.template.defaultfilters import pluralize


CONFIRM_ERR_DICT = {'required': _('Please confirm your password')}


class PasswordField(forms.CharField):
    special_characters = '!@#$%^&*()_+|\/.,~?><:{}'
    password_re = re.compile('^.*(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[%s]).*$'
                             % special_characters)
    has_clone = False
    validate_password = RegexValidator(
        password_re, _('The password must contain at least one letter, one   \
                               number and one special character'), 'invalid')

    class PasswordInput(forms.PasswordInput):
        class Media:
            js = ('muranodashboard/js/passwordfield.js',)

    def __init__(self, label, *args, **kwargs):
        help_text = kwargs.get('help_text')
        if not help_text:
            help_text = _('Enter a complex password with at least one letter, \
                one number and one special character')

        error_messages = {
            'invalid': self.validate_password.message}
        err_msg = kwargs.get('error_messages')
        if err_msg:
            if err_msg.get('required'):
                error_messages['required'] = err_msg.get('required')

        super(PasswordField, self).__init__(
            min_length=7,
            max_length=255,
            validators=[self.validate_password],
            label=label,
            error_messages=error_messages,
            help_text=help_text,
            widget=self.PasswordInput(render_value=True))

    def is_original(self):
        return hasattr(self, 'original') and self.original

    def clone_field(self):
        self.has_clone = True
        field = copy.deepcopy(self)
        self.original = True
        field.label = _('Confirm password')
        field.error_messages = {
            'required': _('Please confirm your password')
        }
        field.help_text = _('Retype your password')
        return field


class InstanceCountField(forms.IntegerField):
    def clean(self, value):
        self.value = super(InstanceCountField, self).clean(value)
        return self.value

    def postclean(self, form, data):
        value = []
        for dc in range(self.value):
            templates = form.get_unit_templates(data)
            if dc < len(templates) - 1:
                value.append(templates[dc])
            else:
                value.append(templates[-1])
        return value


def with_request(func):
    def update(self, initial):
        request = initial.get('request')
        if request:
            func(self, request, initial)
        else:
            raise forms.ValidationError("Can't get a request information")
    return update


class DataGridField(forms.MultiValueField):
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = DataGridCompound
        super(DataGridField, self).__init__(
            (forms.CharField(required=False), forms.CharField()),
            *args, **kwargs)

    def compress(self, data_list):
        return data_list[1]

    @with_request
    def update(self, request, initial):
        self.widget.update_request(request)
        nodes = []
        instance_count = initial.get('instance_count')
        if instance_count:
            for index in xrange(instance_count):
                nodes.append({'name': 'node' + str(index + 1),
                              'is_sync': index < 2,
                              'is_primary': index == 0})
            self.initial = json.dumps(nodes)


class DomainChoiceField(forms.ChoiceField):
    @with_request
    def update(self, request, initial):
        self.choices = [("", "Not in domain")]
        link = request.__dict__['META']['HTTP_REFERER']
        environment_id = re.search(
            'murano/(\w+)', link).group(0)[7:]
        domains = api.service_list_by_type(request, environment_id,
                                           'activeDirectory')
        self.choices.extend(
            [(domain.name, domain.name) for domain in domains])


class FlavorChoiceField(forms.ChoiceField):
    @with_request
    def update(self, request, initial):
        self.choices = [(flavor.name, flavor.name) for flavor in
                        novaclient(request).flavors.list()]
        for flavor in self.choices:
            if 'medium' in flavor[1]:
                self.initial = flavor[0]
                break


class ImageChoiceField(forms.ChoiceField):
    @with_request
    def update(self, request, initial):
        try:
            # public filter removed
            images, _more = glance.image_list_detailed(request)
        except:
            images = []
            exceptions.handle(request,
                              _("Unable to retrieve public images."))

        image_mapping, image_choices = {}, []
        for image in images:
            murano_property = image.properties.get('murano_image_info')
            if murano_property:
                # convert to dict because
                # only string can be stored in image metadata property
                try:
                    murano_json = ast.literal_eval(murano_property)
                except ValueError:
                    messages.error(request,
                                   _("Invalid value in image metadata"))
                else:
                    title = murano_json.get('title')
                    image_id = murano_json.get('id')
                    if title and image_id:
                        image_mapping[smart_text(title)] = smart_text(image_id)

        for name in sorted(image_mapping.keys()):
            image_choices.append((image_mapping[name], name))
        if image_choices:
            image_choices.insert(0, ("", _("Select Image")))
        else:
            image_choices.insert(0, ("", _("No images available")))

        self.choices = image_choices


class AZoneChoiceField(forms.ChoiceField):
    @with_request
    def update(self, request, initial):
        try:
            availability_zones = novaclient(request).availability_zones.\
                list(detailed=False)
        except:
            availability_zones = []
            exceptions.handle(request,
                              _("Unable to retrieve  availability zones."))

        az_choices = [(az.zoneName, az.zoneName)
                      for az in availability_zones if az.zoneState]
        if az_choices:
            az_choices.insert(0, ("", _("Select Availability Zone")))
        else:
            az_choices.insert(0, ("", _("No availability zones available")))

        self.choices = az_choices


def get_clone_name(name):
    return name + '-clone'


def camelize(name):
    return ''.join([bit.capitalize() for bit in name.split('_')])


def decamelize(name):
    pat = re.compile(r'([A-Z]*[^A-Z]*)(.*)')
    bits = []
    while True:
        head, tail = re.match(pat, name).groups()
        bits.append(head)
        if tail:
            name = tail
        else:
            break
    return '_'.join([bit.lower() for bit in bits])


def explode(string):
    if not string:
        return string
    bits = []
    while True:
        head, tail = string[0], string[1:]
        bits.append(head)
        if tail:
            string = tail
        else:
            break
    return bits


class UpdatableFieldsForm(forms.Form):
    def update_fields(self):
        # duplicate all password fields
        while True:
            index, inserted = 0, False
            for name, field in self.fields.iteritems():
                if isinstance(field, PasswordField) and not field.has_clone:
                    self.fields.insert(index + 1,
                                       get_clone_name(name),
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


class BooleanField(forms.BooleanField):
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = forms.CheckboxInput(attrs={'class': 'checkbox'})
        super(BooleanField, self).__init__(*args, **kwargs)


class ClusterIPField(forms.CharField):
    @staticmethod
    def validate_cluster_ip(request, ip_ranges):
        def perform_checking(ip):
            validate_ipv4_address(ip)
            if not all_matching_cidrs(ip, ip_ranges) and ip_ranges:
                raise forms.ValidationError(_('Specified Cluster Static IP is'
                                              'not in valid IP range'))
            try:
                ip_info = novaclient(request).fixed_ips.get(ip)
            except exceptions.UNAUTHORIZED:
                exceptions.handle(
                    request, _("Unable to retrieve information ",
                               "about fixed IP or IP is not valid."),
                    ignore=True)
            else:
                if ip_info.hostname:
                    raise forms.ValidationError(
                        _('Specified Cluster Static IP is already in use'))
        return perform_checking

    @with_request
    def update(self, request, initial):
        try:
            network_list = novaclient(request).networks.list()
            ip_ranges = [network.cidr for network in network_list]
            ranges = ', '.join(ip_ranges)
        except StandardError:
            ip_ranges, ranges = [], ''
        if ip_ranges:
            self.help_text = _('Select IP from available range: ' + ranges)
        else:
            self.help_text = _('Specify valid fixed IP')
        self.validators = [self.validate_cluster_ip(request, ip_ranges)]
        self.error_messages = {'invalid': validate_ipv4_address.message}

    def postclean(self, form, data):
        # hack to compare two IPs
        ips = []
        for key, field in form.fields.items():
            if isinstance(field, ClusterIPField):
                ips.append(data[key])
        if ips[0] == ips[1]:
            raise forms.ValidationError(_(
                'Listener IP and Cluster Static IP should be different'))


class DatabaseListField(forms.CharField):
    validate_mssql_identifier = RegexValidator(
        re.compile(r'^[a-zA-z_][a-zA-Z0-9_$#@]*$'),
        _((u'First symbol should be latin letter or underscore. Subsequent ' +
           u'symbols can be latin letter, numeric, underscore, at sign, ' +
           u'number sign or dollar sign')))

    default_error_messages = {'invalid': validate_mssql_identifier.message}

    def to_python(self, value):
        """Normalize data to a list of strings."""
        if not value:
            return []
        return [name.strip() for name in value.split(',')]

    def validate(self, value):
        """Check if value consists only of valid names."""
        super(DatabaseListField, self).validate(value)
        for db_name in value:
            self.validate_mssql_identifier(db_name)


class ServiceConfigurationForm(UpdatableFieldsForm):
    def __init__(self, *args, **kwargs):
        super(ServiceConfigurationForm, self).__init__(*args, **kwargs)
        self.attribute_mappings = {}
        self.insert_fields(self.fields_template)
        self.initial = kwargs.get('initial', self.initial)
        self.update_fields()

    EVAL_PREFIX = '$'

    types = {
        'string': forms.CharField,
        'boolean': BooleanField,
        'instance': InstanceCountField,
        'clusterip': ClusterIPField,
        'domain': DomainChoiceField,
        'password': PasswordField,
        'integer': forms.IntegerField,
        'databaselist': DatabaseListField,
        'datagrid': DataGridField,
        'flavor': FlavorChoiceField,
        'image': ImageChoiceField,
        'azone': AZoneChoiceField,
        'text': (forms.CharField, forms.Textarea)
    }

    localizable_keys = set(['label', 'help_text', 'error_messages'])

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

        def append_properties(cls, kwargs):
            props = {}
            for key, value in kwargs.iteritems():
                if isinstance(value, property):
                    props[key] = value
            for key in props.keys():
                del kwargs[key]
            if props:
                return type('cls_with_props', (cls,), props)
            else:
                return cls

        def append_field(field_spec):
            _, cls = parse_spec(field_spec['type'], 'type')
            widget = None
            if type(cls) == tuple:
                cls, widget = cls
            _, kwargs = parse_spec(field_spec)
            kwargs['widget'] = process_widget(kwargs, cls, widget)
            cls = append_properties(cls, kwargs)

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
                for flag in explode(flags_str):
                    flag = flag.upper()
                    if hasattr(re, flag):
                        flags |= getattr(re, flag)
                return RegexValidator(re.compile(regexp, flags))
            else:
                return RegexValidator(re.compile(regexp))

        def is_localizable(keys):
            return set(keys).intersection(self.localizable_keys)

        def parse_spec(spec, keys=[]):
            if not type(keys) == list:
                keys = [keys]
            key = keys and keys[-1] or None
            if type(spec) == dict:
                items = []
                for k, v in spec.iteritems():
                    if not k in ('type', 'name'):
                        k = decamelize(k)
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
                elif (type(spec) in (str, unicode) and
                      spec[0] == self.EVAL_PREFIX):
                    def _get(field):
                        name = self.add_prefix(spec[1:])
                        return self.data.get(name, False)

                    def _set(field, value):
                        field.__dict__[key] = value

                    def _del(field):
                        del field.__dict__[key]

                    return key, property(_get, _set, _del)
                else:
                    return key, spec

        for spec in field_specs:
            append_field(spec)

    def get_unit_templates(self, data):
        def parse_spec(spec):
            if type(spec) == list:
                return [parse_spec(_spec) for _spec in spec]
            elif type(spec) == dict:
                return {parse_spec(k): parse_spec(v)
                        for k, v in spec.iteritems()}
            elif (type(spec) in (str, unicode) and
                  spec[0] == self.EVAL_PREFIX):
                return data.get(spec[1:])
            else:
                return spec
        return [parse_spec(spec) for spec in self.service.unit_templates]

    def extract_attributes(self, attributes):
        def get_data(name):
            if type(name) == dict:
                return {k: get_data(v) for k, v in name.iteritems()}
            else:
                return self.cleaned_data[name]
        for attr_name, field_name in self.attribute_mappings.iteritems():
            attributes[attr_name] = get_data(field_name)

    def clean(self):
        form_data = self.cleaned_data

        def compare(name, label):
            if form_data.get(name) != form_data.get(get_clone_name(name)):
                raise forms.ValidationError(_(u"{0}{1} don't match".format(
                    label, pluralize(2))))

        for name, field in self.fields.iteritems():
            if isinstance(field, PasswordField) and field.is_original():
                compare(name, field.label)

            if hasattr(field, 'postclean'):
                value = field.postclean(self, form_data)
                if value:
                    self.cleaned_data[name] = value

        return self.cleaned_data
