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

from django.conf import urls

from muranodashboard.catalog import views
from muranodashboard.dynamic_ui import services

wizard_view = views.Wizard.as_view(
    services.get_app_forms, condition_dict=services.condition_getter)

urlpatterns = [
    urls.url(r'^$', views.IndexView.as_view(), name='index'),
    urls.url(r'^switch_environment/(?P<environment_id>[^/]+)$',
             views.switch, name='switch_env'),
    urls.url(r'^add/(?P<app_id>[^/]+)/(?P<environment_id>[^/]+)/'
             r'(?P<do_redirect>[^/]+)/(?P<drop_wm_form>[^/]+)$',
             wizard_view, name='add'),
    urls.url(r'^add/(?P<app_id>[^/]+)/(?P<environment_id>[^/]+)$',
             views.deploy, name='deploy'),
    urls.url(r'^quick-add/(?P<app_id>[^/]+)$',
             views.quick_deploy, name='quick_deploy'),
    urls.url(r'^details/(?P<application_id>[^/]+)$',
             views.AppDetailsView.as_view(), name='application_details'),
    urls.url(r'^images/(?P<app_id>[^/]*)',
             views.get_image, name="images"),
    urls.url(r'^supplier-images/(?P<app_id>[^/]*)',
             views.get_supplier_image, name="supplier_images")
]
