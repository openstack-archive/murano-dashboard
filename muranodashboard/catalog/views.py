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
from horizon import tabs
from django import shortcuts
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.utils.http import is_safe_url
from muranodashboard.catalog import tabs as catalog_tabs
from muranodashboard.environments import api
from muranodashboard.environments import views
from muranodashboard.dynamic_ui import services
import re


LOG = logging.getLogger(__name__)
ALL_CATEGORY_NAME = 'All'


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


def is_valid_environment(environment, valid_environments):
    for env in valid_environments:
        if environment.id == env.id:
            return True
    return False


def get_environments_context(request):
    envs = get_available_environments(request)
    context = {'available_environments': envs}
    environment = request.session.get('environment')
    if environment and is_valid_environment(environment, envs):
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


def create_quick_environment(request):
    quick_env_prefix = 'quick-env-'
    quick_env_re = re.compile('^' + quick_env_prefix + '([\d]+)$')

    def parse_number(env):
        match = re.match(quick_env_re, env.name)
        return int(match.group(1)) if match else 0

    numbers = [parse_number(e) for e in api.environments_list(request)]
    new_env_number = 1
    if numbers:
        numbers.sort()
        new_env_number = numbers[-1] + 1

    params = {'name': quick_env_prefix + str(new_env_number)}
    return api.environment_create(request, params)


@login_required
def quick_deploy(request, app_id):
    env = create_quick_environment(request)
    try:
        view = views.Wizard.as_view(services.get_app_forms,
                                    condition_dict=services.condition_getter)
        return view(request, app_id=app_id, environment_id=env.id,
                    do_redirect=True, drop_wm_form=True)
    except:
        api.environment_delete(request, env.id)
        raise


class IndexView(list.ListView):
    paginate_by = 6

    def get_queryset(self):
        category = self.kwargs.get('category', ALL_CATEGORY_NAME)
        query_params = {'type': 'Application'}
        search = self.request.GET.get('search')
        if search:
            query_params['search'] = search
        else:
            if category != ALL_CATEGORY_NAME:
                query_params['category'] = category

        pkgs = []
        with api.handled_exceptions(self.request):
            client = api.muranoclient(self.request)
            pkgs = client.packages.filter(**query_params)
        return pkgs

    def get_template_names(self):
        return ['catalog/index.html']

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['latest_list'] = []

        categories = []
        with api.handled_exceptions(self.request):
            client = api.muranoclient(self.request)
            categories = client.packages.categories()

        if not ALL_CATEGORY_NAME in categories:
            categories.insert(0, ALL_CATEGORY_NAME)
        current_category = self.kwargs.get('category', categories[0])
        context['categories'] = categories
        context['current_category'] = current_category

        search = self.request.GET.get('search')
        if search:
            context['search'] = search

        context.update(get_environments_context(self.request))

        return context


class AppDetailsView(tabs.TabView):
    tab_group_class = catalog_tabs.ApplicationTabs
    template_name = 'catalog/app_details.html'

    app = None

    def get_data(self, **kwargs):
        LOG.debug(('AppDetailsView get_data: {0}'.format(kwargs)))
        app_id = kwargs.get('application_id')
        self.app = api.muranoclient(self.request).packages.get(app_id)
        return self.app

    def get_context_data(self, **kwargs):
        context = super(AppDetailsView, self).get_context_data(**kwargs)
        LOG.debug('AppDetailsView get_context called with kwargs: {0}'.
                  format(kwargs))
        context['app'] = self.app

        context.update(get_environments_context(self.request))

        return context

    def get_tabs(self, request, *args, **kwargs):
        app = self.get_data(**kwargs)
        return self.tab_group_class(request, application=app, **kwargs)
