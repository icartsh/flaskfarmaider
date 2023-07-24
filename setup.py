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

F = Framework.get_instance()
P = create_plugin_instance(config)

try:
    from .presenters import Setting
    from .presenters import Schedule

    P.set_module_list([Setting, Schedule])
except Exception as e:
    P.logger.debug(traceback.format_exc())
