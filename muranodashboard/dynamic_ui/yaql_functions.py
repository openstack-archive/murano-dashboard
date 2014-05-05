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
import types

import yaql.context

from muranodashboard.dynamic_ui import helpers


@yaql.context.ContextAware()
@yaql.context.EvalArg('times', types.IntType)
def _repeat(context, template, times):
    for i in xrange(times):
        context.set_data(i + 1, '$index')
        yield helpers.evaluate(template(), context)


_random_string_counter = None


@yaql.context.EvalArg('pattern', types.StringTypes)
@yaql.context.EvalArg('number', types.IntType)
def _generate_hostname(pattern, number):
    """Replace '#' char in pattern with supplied number, if no pattern is
       supplied generate short and unique name for the host.

    :param pattern: hostname pattern
    :param number: number to replace with in pattern
    :return: hostname
    """
    global _random_string_counter

    if pattern and isinstance(pattern, types.UnicodeType):
        return pattern.replace(u'#', unicode(number))
    elif pattern:
        return pattern.replace('#', str(number))

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


def register(context):
    context.register_function(_repeat, 'repeat')
    context.register_function(_generate_hostname, 'generateHostname')
