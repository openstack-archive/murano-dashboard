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

from django.conf.urls.defaults import patterns, url

from .views import MuranoImageView, AddMuranoImageView


urlpatterns = patterns(
    '',
    url(r'^$', MuranoImageView.as_view(),
        name='index'),

    url(r'^add_image$', AddMuranoImageView.as_view(),
        name='add_image'),

    url(r'^remove_image$', MuranoImageView.as_view(),
        name='remove_image'),
)
