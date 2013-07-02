AD_NAME = 'Active Directory'
IIS_NAME = 'IIS'
ASP_NAME = 'ASP.NET Application'
IIS_FARM_NAME = 'IIS Farm'
ASP_FARM_NAME = 'ASP.NET Farm'

SERVICE_NAMES = (AD_NAME, IIS_NAME, ASP_NAME, IIS_FARM_NAME, ASP_FARM_NAME)


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
