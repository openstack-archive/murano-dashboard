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
import os
import time

from muranodashboard.environments.consts import IMAGE_CACHE_DIR


LOG = logging.getLogger(__name__)

CHUNK_SIZE = 2048

if not os.path.exists(IMAGE_CACHE_DIR):
    os.mkdir(IMAGE_CACHE_DIR)
    LOG.info('Creating image cache directory located at {dir}'.
             format(dir=IMAGE_CACHE_DIR))
LOG.info('Using image cache directory located at {dir}'.
         format(dir=IMAGE_CACHE_DIR))


def load_from_file(file_name):
    if os.path.exists(file_name):
        data = []
        with open(file_name, 'rb') as f:
            buf = f.read(CHUNK_SIZE)
            while buf:
                data.append(buf)
                buf = f.read(CHUNK_SIZE)
        return data
    else:
        return None


class ImageCache(object):
    """
    Cache is a map which keeps the filenames for images
    """
    #TODO (gokrokve) define this as a config parameter
    max_cached_count = 120
    #TODO (gokrokve) define this as a config parameter
    cache_age = 120

    def __init__(self, **kwargs):
        self.cache = {}
        self.last_clean = time.time()

    def get_entry(self, name):
        entry = self.cache.get(name, None)
        if entry is None:
            return
        else:
            LOG.debug("Cached entry: %s" % name)
            data = load_from_file(entry['file_name'])
            entry['last_updated'] = time.time()
            return data

    def put_cache(self, name, file_name):
        self.cache[name] = {
            'file_name': file_name,
            'last_updated': time.time()
        }

    def clean(self):
        LOG.debug("Clean cache entries.")
        current_time = time.time()
        for k, v in self.cache.iteritems():
            if current_time - v['last_updated'] > self.cache_age:
                LOG.debug("Remove old entry %s" % k)
                self.cache.pop(k)
