import os
from oslo.config import cfg

common_group = cfg.OptGroup(name='common', title="common configs")

CommonGroup = [
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
               default='http://172.18.124.203:5000/v2.0/',
               help='keystone url'),
    cfg.StrOpt('murano_url',
               default='http://127.0.0.1:8082',
               help='murano url'),
    cfg.StrOpt('keypair_name',
               default='default_key',
               help='keypair for murano services'),
    cfg.StrOpt('asp_git_repository',
               default='git://github.com/',
               help='git repository with asp application'),
    cfg.StrOpt('tomcat_repository',
               default='git://github.com/',
               help='git repository with tomcat servlet'),
    cfg.StrOpt('selenium_server',
               default='http://127.0.0.1:4444/wd/hub',
               help='url where selenium server is running')
]


def register_config(config, config_group, config_opts):

    config.register_group(config_group)
    config.register_opts(config_opts, config_group)

path = os.path.join("%s/config/config_file.conf"
                    % os.getcwd())

if os.path.exists(path):
    cfg.CONF([], project='muranodashboard', default_config_files=[path])

register_config(cfg.CONF, common_group, CommonGroup)

common = cfg.CONF.common
