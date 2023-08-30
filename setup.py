from flask import Response, render_template, jsonify
from werkzeug.local import LocalProxy
from flask_sqlalchemy.query import Query
from sqlalchemy import desc
from plexapi.server import PlexServer

from framework.init_main import Framework
from framework.scheduler import Job as FrameworkJob
from plugin.create_plugin import create_plugin_instance
from plugin.create_plugin import PluginBase
from plugin.logic_module_base import PluginModuleBase, PluginPageBase
from plugin.model_base import ModelBase

from .constants import SCHEDULE, SETTING, TOOL, TOOL_TRASH, MANUAL, LOG

config = {
    'filepath' : __file__,
    'use_db': True,
    'use_default_setting': True,
    'home_module': SCHEDULE,
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
                'uri': TOOL,
                'name': '도구',
                'list': [
                    {'uri': TOOL_TRASH, 'name': 'Plex 휴지통 스캔(개발중)'},
                ]
            },
            {
                'uri': MANUAL,
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
LOGGER = PLUGIN.logger

from .presenters import Setting
from .presenters import Schedule
from .presenters import Manual
from .presenters import Tool

PLUGIN.set_module_list([Setting, Schedule, Manual, Tool])
