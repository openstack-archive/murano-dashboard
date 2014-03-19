#    Copyright (c) 2014 Mirantis, Inc.
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

from django.conf.urls import patterns, url
from muranodashboard.catalog import views
from muranodashboard.catalog import image


VIEW_MOD = 'muranodashboard.catalog.views'

urlpatterns = patterns(
    VIEW_MOD,
    url(r'^index$', views.IndexView.as_view(), name='index'),
    url(r'^index/(?P<category>[^/]+)/(?P<page>\d+)$',
        views.IndexView.as_view(),
        name='index'),
    url(r'^switch_environment/(?P<environment_id>[^/]+)$',
        'switch',
        name='switch_env'),
    url(r'^details/(?P<application_id>[^/]+)$',
        views.AppDetailsView.as_view(), name='application_details'),
    url(r'^images/(?P<image_name>[^/]*)', image.get_image, name="images")
)
