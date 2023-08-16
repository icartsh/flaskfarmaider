import traceback
from plugin.create_plugin import create_plugin_instance # type: ignore
from framework.init_main import Framework # type: ignore

SETTING = 'setting'
SCHEDULE = 'schedule'
LOG = 'log'

config = {
    'filepath' : __file__,
    'use_db': True,
    'use_default_setting': True,
    'home_module': None,
    'menu': {
        'uri': __package__,
        'name': 'FLASKFARMAIDER',
        'list': [
            {
                'uri': SETTING,
                'name': '설정',
            },
            {
                'uri': SCHEDULE,
                'name': '일정',
            },
            {
                'uri': 'manual/README.md',
                'name': '도움말',
            },
            {
                'uri': LOG,
                'name': '로그',
            },
        ]
    },
    'setting_menu': None,
    'default_route': 'normal',
}

P = create_plugin_instance(config)
PLUGIN = P
FRAMEWORK = Framework.get_instance()
def get_plex_mate():
    return FRAMEWORK.PluginManager.get_plugin_instance('plex_mate')
PLUGIN.get_plex_mate = get_plex_mate
LOGGER = PLUGIN.logger

try:
    from .presenters import Setting
    from .presenters import Schedule

    PLUGIN.set_module_list([Setting, Schedule])
except Exception as e:
    LOGGER.debug(traceback.format_exc())
