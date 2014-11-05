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

from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import tables
from openstack_dashboard.api import glance


class MarkImage(tables.LinkAction):
    name = "mark_image"
    verbose_name = _("Mark Image")
    url = "horizon:murano:images:mark_image"
    classes = ("ajax-modal",)
    icon = "plus"

    def allowed(self, request, image):
        return True


class RemoveImageMetadata(tables.DeleteAction):
    data_type_singular = _('Metadata')
    data_type_plural = _('Metadata')

    def delete(self, request, obj_id):
        try:
            glance.image_update(request, obj_id,
                                purge_props='murano_image_info')
        except Exception:
            exceptions.handle(request, _('Unable to remove metadata'),
                              redirect='horizon:murano:images:index')


class MarkedImagesTable(tables.DataTable):
    image = tables.Column(
        'name',
        link='horizon:project:images:images:detail',
        verbose_name=_('Image')
    )
    type = tables.Column('type', verbose_name=_('Type'))
    title = tables.Column('title', verbose_name=_('Title'))

    class Meta:
        name = 'marked_images'
        verbose_name = _('Marked Images')
        table_actions = (MarkImage, RemoveImageMetadata)
        row_actions = (RemoveImageMetadata,)
