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
import os
import tempfile
from django.conf import settings

#---- Metadata Consts ----#
CHUNK_SIZE = 1 << 20  # 1MB
ARCHIVE_PKG_NAME = 'archive.tar.gz'
CACHE_DIR = getattr(settings, 'METADATA_CACHE_DIR',
                    os.path.join(tempfile.gettempdir(),
                                 'muranodashboard-cache'))
IMAGE_CACHE_DIR = getattr(settings, 'IMAGE_CACHE_DIR',
                          os.path.join(tempfile.gettempdir(),
                                       'muranodashboard-image-cache'))

CACHE_REFRESH_SECONDS_INTERVAL = 5

#---- Forms Consts ----#
STATUS_ID_READY = 'ready'
STATUS_ID_PENDING = 'pending'
STATUS_ID_DEPLOYING = 'deploying'
STATUS_ID_NEW = 'new'

DEP_STATUS_ID_RUNNING = 'running'
DEP_STATUS_ID_RUNNING_W_ERRORS = 'running_w_errors'
DEP_STATUS_ID_RUNNING_W_WARNINGS = 'running_w_warnings'
DEP_STATUS_ID_COMPLETED_W_ERRORS = 'completed_w_errors'
DEP_STATUS_ID_COMPLETED_W_WARNINGS = 'completed_w_warnings'
DEP_STATUS_ID_SUCCESS = 'success'

STATUS_CHOICES = (
    (None, True),
    ('Ready to configure', True),
    ('Ready', True),
    ('Configuring', False),
)

STATUS_DISPLAY_CHOICES = (
    (STATUS_ID_READY, 'Ready'),
    (STATUS_ID_DEPLOYING, 'Deploy in progress'),
    (STATUS_ID_PENDING, 'Configuring'),
    (STATUS_ID_NEW, 'Ready to configure'),
    ('', 'Ready to configure'),
)

DEPLOYMENT_STATUS_DISPLAY_CHOICES = (
    (DEP_STATUS_ID_COMPLETED_W_ERRORS, 'Failed'),
    (DEP_STATUS_ID_COMPLETED_W_WARNINGS, 'Completed with warnings'),
    (DEP_STATUS_ID_RUNNING, 'Running'),
    (DEP_STATUS_ID_RUNNING_W_ERRORS, 'Running with errors'),
    (DEP_STATUS_ID_RUNNING_W_WARNINGS, 'Running with warnings'),
    (DEP_STATUS_ID_SUCCESS, 'Successful'),
    ('', 'Unknown'),
)

#---- Logs in Table Consts ----#
LOG_LEVEL_TO_COLOR = {
    'warning': "DF7401",
    'error': "FF0000"
}

LOG_LEVEL_TO_TEXT = {
    'warning': "Warning",
    'error': "Error"
}
