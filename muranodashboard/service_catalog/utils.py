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
from django.utils.translation import ugettext as _
from .tables import DeleteFile, DownloadFile
from horizon import tables, workflows, forms
from muranodashboard.environments.services.forms import UpdatableFieldsForm
from muranodashboard.environments.services.fields import TableField
from muranodashboard.environments.services.fields import Column, CheckColumn
LOG = logging.getLogger(__name__)


STEP_NAMES = [('ui', _('UI Files')), ('workflows', _('Workflows')),
              ('heat', _('Heat Templates')), ('agent', _('Agent Templates')),
              ('scripts', _('Scripts'))]


class CheckboxInput(forms.CheckboxInput):
    def __init__(self):
        super(CheckboxInput, self).__init__(attrs={'class': 'checkbox'})


class Action(workflows.Action, UpdatableFieldsForm):
    def __init__(self, request, context, *args, **kwargs):
        super(Action, self).__init__(request, context, *args, **kwargs)
        self.update_fields(request=request)


def define_tables(table_name, step_verbose_name):
    class ObjectsTable(tables.DataTable):
        file_name = tables.Column('filename', verbose_name=_('File Name'))
        path = tables.Column('path', verbose_name=_('Nested Path'))

        def get_object_display(self, obj):
            return unicode(obj.filename)

        class Meta:
            name = table_name
            verbose_name = step_verbose_name
            table_actions = (DeleteFile,
                             )

            row_actions = (DownloadFile,
                           DeleteFile,
                           )

    return ObjectsTable


def make_table_cls(field_name):
    class MetadataObjectsTableNoActions(tables.DataTable):
        filename = Column('filename', verbose_name=_('File Name'),
                          table_name=field_name)
        path = Column('path', verbose_name=_('Path'), table_name=field_name)
        selected = CheckColumn('selected', verbose_name=_('Selected'),
                               table_name=field_name)

        class Meta:
            template = 'common/form-fields/data-grid/data_table.html'

    return MetadataObjectsTableNoActions


def make_files_step(field_name, step_verbose_name):
    field_instance = TableField(label=_('Selected Files'),
                                table_class=make_table_cls(field_name),
                                js_buttons=False)

    class IntermediateAction(Action):
        def handle(self, request, context):
            files = []
            for item in context[field_name]:
                if item['selected']:
                    if item.get('path'):
                        files.append('{path}/{filename}'.format(**item))
                    else:
                        files.append(item['filename'])
            return {field_name: files}

    class Meta:
        name = step_verbose_name

    # action class name should be different for every different form,
    # otherwise they all look the same
    action_cls = type('FinalAction__%s' % field_name, (IntermediateAction,),
                      {field_name: field_instance,
                       'Meta': Meta})

    class AddFileStep(workflows.Step):
        action_class = action_cls
        template_name = 'service_catalog/_workflow_step_files.html'
        contributes = (field_name,)

    return AddFileStep


FILE_STEPS = [make_files_step(field_name, step_verbose_name)
              for (field_name, step_verbose_name) in STEP_NAMES]
