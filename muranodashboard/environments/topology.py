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

import json

import types
from django.template.loader import render_to_string
from django.contrib.staticfiles.templatetags.staticfiles import static


def _get_environment_status_message(entity):
    if hasattr(entity, 'status'):
        status = entity.status
    else:
        status = entity['?']['status']

    in_progress = True
    status_message = ''
    if status in ('pending', 'ready'):
        in_progress = False
    if status == 'pending':
        status_message = 'Waiting for deployment'
    elif status == 'ready':
        status_message = 'Deployed'
    elif status == 'deploying':
        status_message = 'Deployment is in progress'
    return in_progress, status_message


def _truncate_type(type_str, num_of_chars):
    if len(type_str) < num_of_chars:
        return type_str
    else:
        parts = type_str.split('.')
        type_str, type_len = parts[-1], len(parts[-1])
        for part in reversed(parts[:-1]):
            if type_len + len(part) + 1 > num_of_chars:
                return '...' + type_str
            else:
                type_str = part + '.' + type_str
                type_len += len(part) + 1
        return type_str


def _application_info(application, app_image, status):
    context = {'name': application['name'],
               'type': _truncate_type(application['?']['type'], 45),
               'status': status,
               'app_image': app_image}
    return render_to_string('services/_application_info.html',
                            context)


def _unit_info(unit, unit_image):
    data = dict(unit)
    data['type'] = _truncate_type(data['type'], 45)
    context = {'data': data,
               'unit_image': unit_image}

    return render_to_string('services/_unit_info.html', context)


def _environment_info(environment, status):
    context = {'name': environment.name,
               'status': status}
    return render_to_string('services/_environment_info.html',
                            context)


def _create_empty_node():
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


def _create_ext_network_node(name):
    node = _create_empty_node()
    node.update({'name': name,
                 'image': static('dashboard/img/lb-green.svg'),
                 'link_type': 'relation'})
    return node


def _split_seq_by_predicate(seq, predicate):
    holds, not_holds = [], []
    for elt in seq:
        if predicate(elt):
            holds.append(elt)
        else:
            not_holds.append(elt)
    return holds, not_holds


def _is_atomic(elt):
    key, value = elt
    return not isinstance(value, (types.DictType, types.ListType))


def render_d3_data(environment):
    if not environment:
        return None

    ext_net_name = None
    d3_data = {"nodes": [], "environment": {}}

    in_progress, status_message = _get_environment_status_message(environment)
    environment_node = _create_empty_node()
    environment_node.update({
        'id': environment.id,
        'name': environment.name,
        'status': status_message,
        'image': static('dashboard/img/stack-green.svg'),
        'in_progress': in_progress,
        'info_box': _environment_info(environment, status_message)
    })
    d3_data['environment'] = environment_node

    service_image = static('dashboard/img/stack-green.svg')
    unit_image = static('dashboard/img/server-green.svg')

    for service in environment.services:
        in_progress, status_message = _get_environment_status_message(service)
        required_by = None
        if hasattr(service, 'assignFloatingIP'):
            if ext_net_name:
                required_by = ext_net_name
            else:
                ext_net_name = 'External_Network'
                ext_network_node = _create_ext_network_node(ext_net_name)
                d3_data['nodes'].append(ext_network_node)
                required_by = ext_net_name

        service_node = _create_empty_node()
        service_node.update({
            'name': service.get('name', ''),
            'status': status_message,
            'image': service_image,
            'id': service['?']['id'],
            'link_type': 'unit',
            'in_progress': in_progress,
            'info_box': _application_info(
                service, service_image, status_message)
        })
        if required_by:
            service_node['required_by'] = [required_by]
        d3_data['nodes'].append(service_node)

        def rec(node_data, node_key, parent_node=None):
            if not isinstance(node_data, types.DictType):
                return
            node_type = node_data.get('?', {}).get('type')
            atomics, containers = _split_seq_by_predicate(
                node_data.iteritems(), _is_atomic)
            if node_type and node_data is not parent_node:
                node = _create_empty_node()
                atomics.extend([('id', node_data['?']['id']),
                                ('type', node_type),
                                ('name', node_data.get('name', node_key))])
                if parent_node is not None:
                    node['required_by'] = [parent_node['?']['id']]
                node.update({
                    'id': node_data['?']['id'],
                    'info_box': _unit_info(atomics, unit_image),
                    'image': unit_image,
                    'link_type': 'unit',
                    'in_progress': in_progress})
                d3_data['nodes'].append(node)

            for key, value in containers:
                if key == '?':
                    continue
                if isinstance(value, types.DictType):
                    rec(value, key, node_data)
                elif isinstance(value, types.ListType):
                    for index, val in enumerate(value):
                        rec(val, '{0}[{1}]'.format(key, index), node_data)

        rec(service, None, service)

    return json.dumps(d3_data)
