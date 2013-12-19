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

import re


def camelize(name):
    return ''.join([bit.capitalize() for bit in name.split('_')])


def decamelize(name):
    pat = re.compile(r'([A-Z]*[^A-Z]*)(.*)')
    bits = []
    while True:
        head, tail = re.match(pat, name).groups()
        bits.append(head)
        if tail:
            name = tail
        else:
            break
    return '_'.join([bit.lower() for bit in bits])


def explode(string):
    if not string:
        return string
    bits = []
    while True:
        head, tail = string[0], string[1:]
        bits.append(head)
        if tail:
            string = tail
        else:
            break
    return bits
