import os
from oslo_config import cfg

murano_group = cfg.OptGroup(name='murano', title="murano configs")

MuranoGroup = [
    cfg.StrOpt('horizon_url',
               default='http://127.0.0.1/horizon',
               help="murano dashboard url"),
    cfg.StrOpt('user',
               default='admin',
               help="keystone user"),
    cfg.StrOpt('password',
               default='pass',
               help="password for keystone user"),
    cfg.StrOpt('tenant',
               default='admin',
               help='keystone tenant'),
    cfg.StrOpt('keystone_url',
               default='http://localhost:5000/v2.0/',
               help='keystone url'),
    cfg.StrOpt('murano_url',
               default='http://127.0.0.1:8082',
               help='murano url'),
    cfg.IntOpt('items_per_page',
               default=20,
               help='items per page displayed'),
]


def register_config(config, config_group, config_opts):

    config.register_group(config_group)
    config.register_opts(config_opts, config_group)

path = os.path.join(os.path.dirname(__file__), "config.conf")

if os.path.exists(path):
    cfg.CONF([], project='muranodashboard', default_config_files=[path])

register_config(cfg.CONF, murano_group, MuranoGroup)

common = cfg.CONF.murano
