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

AD_NAME = 'activeDirectory'
IIS_NAME = 'webServer'
ASP_NAME = 'aspNetApp'
IIS_FARM_NAME = 'aspNetAppFarm'
ASP_FARM_NAME = 'webServerFarm'
MSSQL_NAME = 'msSqlServer'

SERVICE_NAMES = (AD_NAME, IIS_NAME, ASP_NAME,
                 IIS_FARM_NAME, ASP_FARM_NAME, MSSQL_NAME)

SERVICE_NAME_DICT = {AD_NAME: 'Active Directory',
                     IIS_NAME: 'IIS',
                     ASP_NAME: 'ASP.NET Application',
                     IIS_FARM_NAME: 'IIS Farm',
                     ASP_FARM_NAME: 'ASP.NET Farm',
                     MSSQL_NAME: 'MS SQL Server'}

STATUS_ID_READY = 'ready'
STATUS_ID_PENDING = 'pending'
STATUS_ID_DEPLOYING = 'deploying'
STATUS_ID_NEW = 'new'

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
