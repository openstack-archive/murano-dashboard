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

from djblets.datagrid.grids import Column, DataGrid
from models import Node, FakeQuerySet
import floppyforms as forms
import json
import re
from django.contrib.auth.models import SiteProfileNotAvailable


class PK(object):
    def __init__(self, value=0):
        self.value = value

    def next(self):
        self.value += 1
        return self.value

    def current(self):
        return self.value


class CheckColumn(Column):
    def render_data(self, item):
        checked = getattr(item, self.field_name)
        checked = 'checked="checked"' if checked else ''
        return '<input type="checkbox" %s/>' % (checked,)


class RadioColumn(Column):
    def __init__(self, *args, **kwargs):
        self.name = kwargs.get('name', 'default')
        super(RadioColumn, self).__init__(*args, **kwargs)

    def render_data(self, item):
        checked = getattr(item, self.field_name)
        checked = 'checked="checked"' if checked else ''
        name = 'name="%s"' % (self.name,)
        return '<input type="radio" %s %s/>' % (name, checked)


class NodeDataGrid(DataGrid):
    name = Column('Node', sortable=False)
    is_sync = CheckColumn('Sync')
    is_primary = RadioColumn('Primary')

    def __init__(self, request, data):
        self.pk = PK()
        items = []
        if type(data) in (str, unicode):
            # BEWARE, UGLY HACK!!! Data should be list there already!
            data = json.loads(data)
        for kwargs in data:
            items.append(Node(**dict(kwargs.items() +
                                     [('id', self.pk.next())])))
        super(NodeDataGrid, self).__init__(request, FakeQuerySet(
            Node, items=items), optimize_sorts=False)
        self.default_sort = []
        self.default_columns = ['name', 'is_sync', 'is_primary']

    # hack
    def load_state(self, render_context=None):
        if self.request.user.is_authenticated():
            def get_profile():
                raise SiteProfileNotAvailable
            setattr(self.request.user, 'get_profile', get_profile)
        super(NodeDataGrid, self).load_state(render_context)


class DataGridWidget(forms.widgets.Input):
    template_name = 'data_grid_field.html'

    def get_context(self, name, value, attrs=None):
        ctx = super(DataGridWidget, self).get_context_data()
        ctx['data_grid'] = NodeDataGrid(self.request, data=value)
        return ctx

    def value_from_datadict(self, data, files, name):
        base, match = None, re.match('(.*)_[0-9]+', name)
        if match:
            base = match.group(1)
        if base:
            pattern = re.compile(base + '_[0-9]+')
            for key in data:
                if re.match(pattern, key):
                    return data[key]
        return super(DataGridWidget, self).value_from_datadict(
            data, files, name)

    class Media:
        css = {'all': ('css/datagrid.css',
                       'muranodashboard/css/datagridfield.css')}
        js = ('js/jquery.gravy.js',
              'js/datagrid.js',
              'muranodashboard/js/datagridfield.js')


class DataGridCompound(forms.MultiWidget):
    def __init__(self, attrs=None):
        _widgets = (DataGridWidget(),
                    forms.HiddenInput(attrs={'class': 'gridfield-hidden'}))
        super(DataGridCompound, self).__init__(_widgets, attrs)

    def update_request(self, request):
        self.widgets[0].request = request

    def decompress(self, value):
        if value != '':
            return [json.loads(value), value]
        else:
            return [None, None]
