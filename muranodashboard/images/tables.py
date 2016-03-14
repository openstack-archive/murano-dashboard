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

from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy
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
        return request.user.is_superuser


class RemoveImageMetadata(tables.DeleteAction):
    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Metadata",
            u"Delete Metadata",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Deleted Metadata",
            u"Deleted Metadata",
            count
        )

    def delete(self, request, obj_id):
        try:
            properties = glance.image_get(request, obj_id).properties
            properties.pop('murano_image_info', None)
            glance.image_update(request, obj_id, properties=properties,
                                purge_props=True)
        except Exception:
            exceptions.handle(request, _('Unable to remove metadata'),
                              redirect=reverse('horizon:murano:images:index'))

    def allowed(self, request, image):
        return request.user.is_superuser


class MarkedImagesTable(tables.DataTable):
    image = tables.Column(
        'name',
        link='horizon:project:images:images:detail',
        verbose_name=_('Image')
    )
    type = tables.Column(lambda obj: getattr(obj, 'type', None),
                         verbose_name=_('Type'))
    title = tables.Column(lambda obj: getattr(obj, 'title', None),
                          verbose_name=_('Title'),
                          truncate=40)

    class Meta(object):
        name = 'marked_images'
        verbose_name = _('Marked Images')
        table_actions = (MarkImage, RemoveImageMetadata)
        row_actions = (RemoveImageMetadata,)
