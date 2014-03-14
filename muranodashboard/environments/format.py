# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from django.template.loader import render_to_string


def get_environment_status_message(entity):
    try:
        status = entity['status']
    except TypeError:
        status = entity.status

    in_progress = True
    if status in ('pending', 'ready'):
        in_progress = False
    if status == 'pending':
        status_message = 'Waiting for deployment'
    elif status == 'ready':
        status_message = 'Deployed'
    elif status == 'deploying':
        status_message = 'Deployment is in progress'
    return in_progress, status_message


def appication_info(application, app_image, status):
    context = {}
    context['name'] = application['name']
    context['type'] = application['type']
    context['status'] = status
    context['app_image'] = app_image
    return render_to_string('services/_application_info.html',
                            context)


def unit_info(service, unit, unit_image):
    context = {}
    context['name'] = unit['name']
    context['os'] = service['osImage']['type']
    context['image'] = service['osImage']['name']
    context['flavor'] = service['flavor']
    context['unit_image'] = unit_image
    return render_to_string('services/_unit_info.html',
                            context)


def environment_info(environment, status):
    context = {}
    context['name'] = environment.name
    context['status'] = status
    return render_to_string('services/_environment_info.html',
                            context)


def create_empty_node():
    node = {
        'name': '',
        'status': 'ready',
        'image': '',
        'image_size': 60,
        'required_by': [],
        'image_x': -30,
        'image_y': -30,
        'text_x': 40,
        'text_y': ".35em",
        'link_type': "relation",
        'in_progress': False,
        'info_box': ''
    }
    return node


def create_ext_network_node(name):
    node = create_empty_node()
    node['name'] = name
    node['image'] = '/static/dashboard/img/lb-green.svg'
    node['link_type'] = "relation"
    return node
