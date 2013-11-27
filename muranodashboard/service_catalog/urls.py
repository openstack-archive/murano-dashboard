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

from django.conf.urls import patterns, url

from .views import ServiceCatalogView
from .views import UploadServiceView
from .views import ComposeServiceView
from .views import ManageServiceView
from .views import ManageFilesView
from .views import UploadFileView, UploadFileView2


urlpatterns = patterns(
    '',
    url(r'^$', ServiceCatalogView.as_view(),
        name='index'),

    url(r'^upload_service$', UploadServiceView.as_view(),
        name='upload_service'),

    url(r'^upload_file/(?P<data_type>[^/]+)$',
        UploadFileView2.as_view(),
        name='upload_file2'),

    url(r'^manage_files/upload_file$', UploadFileView.as_view(),
        name='upload_file'),
    #This should goes first
    url(r'^manage_files/(?P<full_service_name>[^/]+)?$',
        ManageServiceView.as_view(),
        name='manage_service'),

    url(r'^manage_files', ManageFilesView.as_view(),
        name='manage_files'),

    url(r'^compose_service/(?P<full_service_name>[^/]+)?$',
        ComposeServiceView.as_view(),
        name='compose_service'),

)
