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

import os
from django.http import HttpResponse
from muranodashboard import catalog
from muranodashboard.catalog import models


def get_image(request, image_name):
    path = os.path.basename(request.path)
    if path:
        cache = catalog.get_image_cache()
        data = cache.get_entry(path)
        if data:
            response = generate_response(data)
            return response
        else:
            #TODO(gokrokve) emulate download from API
            cache.put_cache(path, path)
            response = generate_response(models.get_image(path))
            return response
    else:
        return HttpResponse()


def generate_response(data):
    response = HttpResponse(content_type='image/png')
    for buf in data:
        response.write(buf)
    response['Cache-Control'] = "max-age=604800, public"
    return response
