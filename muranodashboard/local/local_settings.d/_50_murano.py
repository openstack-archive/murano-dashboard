# MURANO_API_URL = "http://localhost:8082"

# Set to True to use Glance Artifact Repository to store murano packages
MURANO_USE_GLARE = False

# Sets the Glance API endpoint to interact with Artifact Repo.
# If left commented the one from keystone will be used
# GLANCE_API_URL = 'http://ubuntu1:9292'

MURANO_REPO_URL = 'http://apps.openstack.org/api/v1/murano_repo/liberty/'

# Overrides the default dashboard name (Murano) that is displayed
# in the main accordion navigation
# MURANO_DASHBOARD_NAME = "Murano"

# Specify a maximum number of limit packages.
# PACKAGES_LIMIT = 100

# Set default session backend from browser cookies to database to
# avoid issues with forms during creating applications.
DATABASES = {
    'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': 'murano-dashboard.sqlite',
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
