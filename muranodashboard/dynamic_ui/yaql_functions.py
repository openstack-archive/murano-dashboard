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

import random
import string
import time

from yaql.language import specs
from yaql.language import yaqltypes

from muranodashboard.catalog import forms as catalog_forms
from muranodashboard.dynamic_ui import helpers


@specs.parameter('times', int)
def _repeat(context, template, times):
    for i in xrange(times):
        context['index'] = i + 1
        yield helpers.evaluate(template, context)


_random_string_counter = None


@specs.parameter('pattern', yaqltypes.String())
@specs.parameter('number', int)
def _generate_hostname(pattern, number):
    """Generates hostname based on pattern

    Replaces '#' char in pattern with supplied number, if no pattern is
    supplied generates short and unique name for the host.

    :param pattern: hostname pattern
    :param number: number to replace with in pattern
    :return: hostname
    """
    global _random_string_counter

    if pattern:
        # NOTE(kzaitsev) works both for unicode and simple strings in py2
        # and works as expected in py3
        pattern.replace('#', str(number))

    counter = _random_string_counter or 1
    # generate first 5 random chars
    prefix = ''.join(random.choice(string.lowercase) for _ in range(5))
    # convert timestamp to higher base to shorten hostname string
    # (up to 8 chars)
    timestamp = helpers.int2base(int(time.time() * 1000), 36)[:8]
    # third part of random name up to 2 chars
    # (1295 is last 2-digit number in base-36, 1296 is first 3-digit number)
    suffix = helpers.int2base(counter, 36)
    _random_string_counter = (counter + 1) % 1296
    return prefix + timestamp + suffix


def _name(context):
    name = context.get_data[
        catalog_forms.WF_MANAGEMENT_NAME]['application_name']
    return name


def register(context):
    context.register_function(_repeat, 'repeat')
    context.register_function(_generate_hostname, 'generateHostname')
    context.register_function(_name, 'name')
