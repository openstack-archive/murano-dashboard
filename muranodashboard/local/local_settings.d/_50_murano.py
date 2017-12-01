# MURANO_API_URL = "http://localhost:8082"

# Set to True to use Glare Artifact Repository to store murano packages
MURANO_USE_GLARE = False

# Sets the Glare API endpoint to interact with Artifact Repo.
# If left commented the one from keystone will be used
# GLARE_API_URL = 'http://ubuntu1:9494'

MURANO_REPO_URL = 'http://apps.openstack.org/api/v1/murano_repo/liberty/'

DISPLAY_MURANO_REPO_URL = 'http://apps.openstack.org/#tab=murano-apps'

# Overrides the default dashboard name (App Catalog) that is displayed
# in the main accordion navigation
# MURANO_DASHBOARD_NAME = "App Catalog"

# Filter the list of Murano images displayed to be only those owned by this
# project ID
# MURANO_IMAGE_FILTER_PROJECT_ID =

# Specify a maximum number of limit packages.
# PACKAGES_LIMIT = 100

# Make sure horizon has config the DATABASES, If horizon config use horizon's
# DATABASES, if not, set it by murano.
try:
    from openstack_dashboard.settings import DATABASES
    DATABASES_CONFIG = DATABASES.has_key('default')
except ImportError:
    DATABASES_CONFIG = False

# Set default session backend from browser cookies to database to
# avoid issues with forms during creating applications.
if not DATABASES_CONFIG:
    DATABASES = {
        'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'murano-dashboard.sqlite',
        }
    }
SESSION_ENGINE = 'django.contrib.sessions.backends.db'

try:
    from openstack_dashboard import static_settings
    LEGACY_STATIC_SETTINGS = True
except ImportError:
    LEGACY_STATIC_SETTINGS = False

HORIZON_CONFIG['legacy_static_settings'] = LEGACY_STATIC_SETTINGS

# from openstack_dashboard.settings import POLICY_FILES
POLICY_FILES.update({'murano': 'murano_policy.json',})

# Applications using the encryptData/decryptData yaql functions will require
# the below to be configured
#KEY_MANAGER = {
#        'auth_url': 'http://192.168.5.254:5000/v3',
#        'username': 'admin',
#        'user_domain_name': 'default',
#        'password': 'password',
#        'project_name': 'admin',
#        'project_domain_name': 'default'
#}

