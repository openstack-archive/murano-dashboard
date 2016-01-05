#    Copyright (c) 2015 Mirantis, Inc.
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

from muranoclient.common import exceptions as muranoclient_exc


RECOVERABLE = (muranoclient_exc.HTTPException,
               muranoclient_exc.HTTPForbidden,
               muranoclient_exc.CommunicationError)

NOT_FOUND = (muranoclient_exc.NotFound,
             muranoclient_exc.EndpointNotFound)

UNAUTHORIZED = (muranoclient_exc.HTTPUnauthorized,)
