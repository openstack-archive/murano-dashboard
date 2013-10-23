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
from horizon import messages
from openstack_dashboard.api import glance


class MuranoImages(tables.LinkAction):
    name = 'show_images'
    verbose_name = _('Murano Images')
    url = 'horizon:murano:images:murano_images'

    def allowed(self, request, environment):
        return True


class AddMuranoImage(tables.LinkAction):
    name = "add_image"
    verbose_name = _("Add Image")
    url = "horizon:murano:images:add_image"
    classes = ("ajax-modal", "btn-create")

    def allowed(self, request, image):
        return True


class RemoveImageMetadata(tables.DeleteAction):
    data_type_singular = _('Murano Metadata')
    data_type_plural = _('Murano Metadata')

    def delete(self, request, obj_id):
        try:
            glance.image_update(request, obj_id, properties={})
            messages.success(request, _('Image removed from Murano.'))
        except Exception:
            exceptions.handle(request, _('Unable to update image.'))


class ImagesTable(tables.DataTable):
    image_title = tables.Column('title', verbose_name=_('Murano title'))
    image_id = tables.Column('id', verbose_name=_('Image id'))

    image_name = tables.Column('name', verbose_name=_('Name in Glance'))
    image_type = tables.Column('name', verbose_name=_('Murano Type'))

    class Meta:
        name = 'images'
        verbose_name = _('Murano Images')
        table_actions = (AddMuranoImage, RemoveImageMetadata)
        row_actions = (RemoveImageMetadata,)
