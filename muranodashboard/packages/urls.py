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

from django.conf import urls

from muranodashboard.packages import views


urlpatterns = [
    urls.url(r'^$', views.PackageDefinitionsView.as_view(), name='index'),
    urls.url(r'^upload$', views.ImportPackageWizard.as_view(
             views.FORMS), name='upload'),
    urls.url(r'^import_bundle$', views.ImportBundleWizard.as_view(
             views.BUNDLE_FORMS), name='import_bundle'),
    urls.url(r'^modify/(?P<app_id>[^/]+)?$',
             views.ModifyPackageView.as_view(), name='modify'),
    urls.url(r'^(?P<app_id>[^/]+)?$',
             views.DetailView.as_view(), name='detail'),
    urls.url(r'^download/(?P<app_name>[^/]+)/(?P<app_id>[^/]+)?$',
             views.download_packge, name='download'),
]
