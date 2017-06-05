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

from openstack_dashboard.dashboards.project.instances import views as inst_view

from muranodashboard.environments import views

ENVIRONMENT_ID = r'^(?P<environment_id>[^/]+)'

urlpatterns = [
    urls.url(r'^environments/$', views.IndexView.as_view(), name='index'),
    urls.url(r'^create_environment$', views.CreateEnvironmentView.as_view(),
             name='create_environment'),
    urls.url(ENVIRONMENT_ID + r'/services$',
             views.EnvironmentDetails.as_view(), name='services'),
    urls.url(ENVIRONMENT_ID + r'/services/get_d3_data$',
             views.JSONView.as_view(), name='d3_data'),
    urls.url(ENVIRONMENT_ID + r'/(?P<service_id>[^/]+)/$',
             views.DetailServiceView.as_view(), name='service_details'),
    urls.url(ENVIRONMENT_ID + r'/start_action/(?P<action_id>[^/]+)/$',
             views.StartActionView.as_view(), name='start_action'),
    urls.url(ENVIRONMENT_ID +
             r'/actions/(?P<task_id>[^/]+)(?:/(?P<optional>[^/]+))?/$',
             views.ActionResultView.as_view(), name='action_result'),
    urls.url(r'^(?P<instance_id>[^/]+)/$',
             inst_view.DetailView.as_view(), name='detail'),
    urls.url(r'^deployment_history$', views.DeploymentHistoryView.as_view(),
             name='deployment_history'),
    urls.url(ENVIRONMENT_ID + r'/deployments/(?P<deployment_id>[^/]+)$',
             views.DeploymentDetailsView.as_view(), name='deployment_details'),
]
