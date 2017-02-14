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
from django.utils.translation import ugettext_lazy as _


# ---- Metadata Consts ---- #
CHUNK_SIZE = 1 << 20  # 1MB
ARCHIVE_PKG_NAME = 'archive.tar.gz'
CACHE_DIR = getattr(settings, 'METADATA_CACHE_DIR',
                    os.path.join(tempfile.gettempdir(),
                                 'muranodashboard-cache'))

CACHE_REFRESH_SECONDS_INTERVAL = 5

DASHBOARD_ATTRS_KEY = '_26411a1861294160833743e45d0eaad9'

# ---- Forms Consts ---- #
STATUS_ID_READY = 'ready'
STATUS_ID_PENDING = 'pending'
STATUS_ID_DEPLOYING = 'deploying'
STATUS_ID_DELETING = 'deleting'
STATUS_ID_DELETE_FAILURE = 'delete failure'
STATUS_ID_DEPLOY_FAILURE = 'deploy failure'
STATUS_ID_NEW = 'new'

NO_ACTION_ALLOWED_STATUSES = (STATUS_ID_DEPLOYING,
                              STATUS_ID_DELETING)

DEP_STATUS_ID_RUNNING = 'running'
DEP_STATUS_ID_RUNNING_W_ERRORS = 'running_w_errors'
DEP_STATUS_ID_RUNNING_W_WARNINGS = 'running_w_warnings'
DEP_STATUS_ID_COMPLETED_W_ERRORS = 'completed_w_errors'
DEP_STATUS_ID_COMPLETED_W_WARNINGS = 'completed_w_warnings'
DEP_STATUS_ID_SUCCESS = 'success'

# A tuple of tuples representing the possible data values for the
# status column and their associated boolean equivalent. Positive
# states should equate to ``True``, negative states should equate
# to ``False``, and indeterminate states should be ``None``.
# When value is None progress bar will be displayed.

STATUS_CHOICES = (
    (None, True),
    (STATUS_ID_READY, True),
    (STATUS_ID_PENDING, True),
    (STATUS_ID_DEPLOYING, None),
    (STATUS_ID_DELETING, None),
    (STATUS_ID_NEW, True),
    (STATUS_ID_DELETE_FAILURE, False),
    (STATUS_ID_DEPLOY_FAILURE, False),
)

DEPLOYMENT_STATUS_CHOICES = (
    (None, True),
    (DEP_STATUS_ID_RUNNING, True),
    (DEP_STATUS_ID_SUCCESS, True),
    (DEP_STATUS_ID_RUNNING_W_ERRORS, False),
    (DEP_STATUS_ID_RUNNING_W_WARNINGS, False),
    (DEP_STATUS_ID_COMPLETED_W_WARNINGS, False),
    (DEP_STATUS_ID_COMPLETED_W_ERRORS, False),
)

STATUS_DISPLAY_CHOICES = (
    (STATUS_ID_READY, _('Ready')),
    (STATUS_ID_DEPLOYING, _('Deploying')),
    (STATUS_ID_DELETING, _('Deleting')),
    (STATUS_ID_PENDING, _('Ready to deploy')),
    (STATUS_ID_NEW, _('Ready to configure')),
    (STATUS_ID_DELETE_FAILURE, _('Delete failure')),
    (STATUS_ID_DEPLOY_FAILURE, _('Deploy failure')),
    ('', _('Ready to configure')),
)

DEPLOYMENT_STATUS_DISPLAY_CHOICES = (
    (DEP_STATUS_ID_COMPLETED_W_ERRORS, _('Failed')),
    (DEP_STATUS_ID_COMPLETED_W_WARNINGS, _('Completed with warnings')),
    (DEP_STATUS_ID_RUNNING, _('Running')),
    (DEP_STATUS_ID_RUNNING_W_ERRORS, _('Running with errors')),
    (DEP_STATUS_ID_RUNNING_W_WARNINGS, _('Running with warnings')),
    (DEP_STATUS_ID_SUCCESS, _('Successful')),
    ('', _('Unknown')),
)
