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
import logging
from django.views.generic import list
from django.template import defaultfilters as filters
from django.utils import datastructures
from horizon import tabs
from horizon import workflows

from django import shortcuts
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.utils.http import is_safe_url

from muranodashboard.catalog import tabs as catalog_tabs
from muranodashboard.catalog import models
from muranodashboard.catalog import workflows as murano_workflows
from muranodashboard.environments import api

LOG = logging.getLogger(__name__)


class DictToObj(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)


def get_available_environments(request):
    envs = []
    for env in api.environments_list(request):
        obj = DictToObj(id=env.id, name=env.name, status=env.status)
        envs.append(obj)

    return envs


def get_environments_context(request):
    envs = get_available_environments(request)
    context = {'available_environments': envs}
    environment = request.session.get('environment')
    if environment:
        context['environment'] = environment
    elif envs:
        context['environment'] = envs[0]
    return context


@login_required
def switch(request, environment_id, redirect_field_name=REDIRECT_FIELD_NAME):
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    if not is_safe_url(url=redirect_to, host=request.get_host()):
        redirect_to = settings.LOGIN_REDIRECT_URL

    for env in get_available_environments(request):
        if env.id == environment_id:
            request.session['environment'] = env
            break
    return shortcuts.redirect(redirect_to)


class IndexView(list.ListView):
    apps = models.AppCatalogModel()
    categories = models.Categories()
    paginate_by = 6

    def get_queryset(self):
        return self.apps.objects.all()

    def get_template_names(self):
        return ['catalog/index.html']

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['latest_list'] = self.apps.last_objects
        categories = datastructures.SortedDict(
            ((filters.slugify(category), category) for category in
             self.categories.all()))

        current_category = self.kwargs.get('category')
        current_category_name = categories.get(current_category)
        if current_category_name is None and categories:
            current_category_name = categories.values()[0]
        context['categories'] = categories
        context['current_category'] = current_category
        context['current_category_name'] = current_category_name

        context.update(get_environments_context(self.request))

        return context


class AppDetailsView(tabs.TabView):
    tab_group_class = catalog_tabs.ApplicationTabs
    template_name = 'catalog/app_details.html'

    app_model = models.AppCatalogModel.objects
    app = None

    def get_data(self, **kwargs):
        LOG.debug(('AppDetailsView get_data: {0}'.format(kwargs)))
        app_id = kwargs.get('application_id')
        self.app = self.app_model.get_info(app_id)
        return self.app

    def get_context_data(self, **kwargs):
        context = super(AppDetailsView, self).get_context_data(**kwargs)
        LOG.debug('AppDetailsView get_context called with kwargs: {0}'.
                  format(kwargs))
        context['application'] = self.app

        context.update(get_environments_context(self.request))

        return context

    def get_tabs(self, request, *args, **kwargs):
        app = self.get_data(**kwargs)
        return self.tab_group_class(request, application=app, **kwargs)


class AddApplicationView(workflows.WorkflowView):
    workflow_class = murano_workflows.AddApplication
    template_name = 'environments/create.html'

    def get_initial(self):
        initial = super(AddApplicationView, self).get_initial()
        initial.update({'environment_id': self.kwargs.get('environment_id'),
                        'app_id': self.kwargs.get('app_id')})
        return initial
