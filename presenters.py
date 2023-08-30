import json
import traceback
from typing import Any
from urllib.parse import parse_qs
from threading import Thread
import sqlite3

from .models import Job
from .aiders import BrowserAider, SettingAider, JobAider, PlexmateAider
from .setup import PLUGIN, LOGGER, Response, render_template, jsonify, LocalProxy, PluginBase, PluginModuleBase, PluginPageBase
from .constants import SETTING, FRAMEWORK, TASK_KEYS, SCAN_MODE_KEYS, SCHEDULE, SECTION_TYPE_KEYS, STATUSES, README, TOOL, DB_VERSIONS
from .constants import TASKS, STATUS_KEYS, FF_SCHEDULE_KEYS, SCAN_MODES, SECTION_TYPES, FF_SCHEDULES, TOOL_TRASH, MANUAL
from .constants import SETTING_DB_VERSION, SETTING_RCLONE_REMOTE_ADDR, SETTING_RCLONE_REMOTE_VFS, SETTING_RCLONE_REMOTE_USER
from .constants import SETTING_RCLONE_REMOTE_PASS, SETTING_RCLONE_MAPPING, SETTING_PLEXMATE_MAX_SCAN_TIME, SETTING_PLEXMATE_TIMEOVER_RANGE
from .constants import SETTING_PLEXMATE_PLEX_MAPPING, SETTING_STARTUP_EXECUTABLE, SETTING_STARTUP_COMMANDS, SETTING_STARTUP_TIMEOUT, SETTING_STARTUP_DEPENDENCIES
from .constants import SCHEDULE_WORKING_DIRECTORY, SCHEDULE_LAST_LIST_OPTION, TOOL_TRASH_KEYS, TOOL_TRASHES, TOOL_TRASH_TASK_STATUS
from . import migrations


def thread_func(func, *args, **kwds):
    th = Thread(target=func, args=args, kwargs=kwds, daemon=True)
    th.start()
    return th

class Base():

    def __init__(self, *args, **kwds) -> None:
        super().__init__(*args, **kwds)

    def set_recent_menu(self, req: LocalProxy) -> None:
        current_menu = '|'.join(req.path[1:].split('/')[1:])
        if not current_menu == PLUGIN.ModelSetting.get('recent_menu_plugin'):
            LOGGER.debug(f'현재 메뉴 위치 저장: {current_menu}')
            PLUGIN.ModelSetting.set('recent_menu_plugin', current_menu)

    def get_template_args(self) -> dict[str, Any]:
        args = {
            'package_name': PLUGIN.package_name,
            'module_name': self.name if isinstance(self, BaseModule) else self.parent.name,
            'page_name': self.name if isinstance(self, BasePage) else None,
        }
        return args

    def prerender(self, sub: str, req: LocalProxy) -> None:
        self.set_recent_menu(req)

    def task_command(self, task: str, target: str, recursive: str, scan: str) -> tuple[bool, str]:
        if recursive:
            recursive = True if recursive.lower() == 'true' else False
        else:
            recursive = False

        if scan:
            scan_mode, periodic_id = scan.split('|')
        else:
            scan_mode = SCAN_MODE_KEYS[0]
            periodic_id = '-1'

        if target:
            job = {
                'task': task,
                'target': target,
                'recursive': recursive,
                'scan_mode': scan_mode,
                'periodic_id': int(periodic_id) if periodic_id else -1,
            }
            #JobAider().start_job(Job.get_job(info=job))
            thread_func(JobAider().start_job, Job.get_job(info=job))
            result, msg = True, '작업을 실행했습니다.'
        else:
            result, msg = False, '경로 정보가 없습니다.'
        return result, msg


class BaseModule(Base, PluginModuleBase):

    def __init__(self, plugin: PluginBase, first_menu: str = None, name: str = None, scheduler_desc: str = None) -> None:
        '''mod_ins = mod(self) in PluginBase.set_module_list()'''
        super().__init__(plugin, first_menu=first_menu, name=name, scheduler_desc=scheduler_desc)
        self.db_default = {}

    def get_module(self, module_name: str) -> PluginModuleBase | None:
        '''override'''
        return super().get_module(module_name)

    def set_page_list(self, page_list: list[PluginPageBase]) -> None:
        '''override'''
        super().set_page_list(page_list)

    def get_page(self, page_name: str) -> PluginPageBase | None:
        '''override'''
        return super().get_page(page_name)

    def process_menu(self, sub: str, req: LocalProxy) -> Response:
        '''override'''
        self.prerender(sub, req)
        try:
            if self.page_list:
                if sub:
                    page_ins = self.get_page(sub)
                else:
                    page_ins = self.get_page(self.get_first_menu())
                return page_ins.process_menu(req)
            else:
                args = self.get_template_args()
                return render_template(f'{PLUGIN.package_name}_{self.name}.html', args=args)
        except:
            LOGGER.error(traceback.format_exc())
            return render_template('sample.html', title=f"process_menu() - {PLUGIN.package_name}/{self.name}/{sub}")

    def process_ajax(self, sub: str, req: LocalProxy):
        '''override'''
        pass

    def process_command(self, command: str, arg1: str, arg2: str, arg3: str, req: LocalProxy) -> Response:
        '''override'''
        pass

    def process_api(self, sub: str, req: LocalProxy):
        '''override'''
        pass

    def process_normal(self, sub: str, req: LocalProxy):
        '''override'''
        pass

    def scheduler_function(self):
        '''override'''
        pass

    def db_delete(self, day: int | str) -> int:
        '''override'''
        return super().db_delete(day)

    def plugin_load(self):
        '''override'''
        pass

    def plugin_load_celery(self):
        '''override'''
        pass

    def plugin_unload(self):
        '''override'''
        pass

    def setting_save_after(self, change_list):
        '''override'''
        pass

    def process_telegram_data(self, data, target=None):
        '''override'''
        pass

    def migration(self):
        '''override'''
        pass

    def get_scheduler_desc(self) -> str:
        '''override'''
        return super().get_scheduler_desc()

    def get_scheduler_interval(self) -> str:
        '''override'''
        return super().get_scheduler_interval()

    def get_first_menu(self) -> str:
        '''override'''
        return super().get_first_menu()

    def get_scheduler_id(self) -> str:
        '''override'''
        return super().get_scheduler_id()

    def dump(self, data) -> str:
        '''override'''
        return super().dump(data)

    def socketio_connect(self):
        '''override'''
        pass

    def socketio_disconnect(self):
        '''override'''
        pass

    def arg_to_dict(self, arg):
        '''override'''
        return super().arg_to_dict(arg)

    def get_scheduler_name(self):
        '''override'''
        return super().get_scheduler_name()

    def process_discord_data(self, data):
        '''override'''
        pass

    def start_celery(self, func: callable, on_message: callable = None, *args, page: PluginPageBase = None) -> Any:
        '''override'''
        return super().start_celery(func, on_message, *args, page)


class BasePage(Base, PluginPageBase):

    def __init__(self, plugin: PluginBase, parent: PluginModuleBase, name: str = None, scheduler_desc: str = None) -> None:
        '''mod_ins = mod(self.P, self) in PluginModuleBase.set_page_list()'''
        super().__init__(plugin, parent, name=name, scheduler_desc=scheduler_desc)
        self.db_default = {}

    def process_menu(self, req: LocalProxy) -> Response:
        '''override'''
        self.prerender(self.name, req)
        try:
            args = self.get_template_args()
            return render_template(f'{PLUGIN.package_name}_{self.parent.name}_{self.name}.html', args=args)
        except Exception as e:
            self.P.logger.error(traceback.format_exc())
            return render_template('sample.html', title=f"process_menu() - {PLUGIN.package_name}/{self.parent.name}/{self.name}")

    def process_ajax(self, sub: str, req: LocalProxy):
        '''override'''
        pass

    def process_api(self, sub: str, req: LocalProxy):
        '''override'''
        pass

    def process_normal(self, sub: str, req: LocalProxy):
        '''override'''
        pass

    def process_command(self, command: str, arg1: str, arg2: str, arg3: str, req: LocalProxy) -> Response:
        '''override'''
        pass

    def plugin_load(self):
        '''override'''
        pass

    def plugin_load_celery(self):
        '''override'''
        pass

    def plugin_unload(self):
        '''override'''
        pass

    def scheduler_function(self):
        '''override'''
        pass

    def get_scheduler_desc(self) -> str:
        '''override'''
        return super().get_scheduler_desc()

    def get_scheduler_interval(self) -> str:
        '''override'''
        return super().get_scheduler_interval()

    def get_scheduler_name(self) -> str:
        '''override'''
        return super().get_scheduler_name()

    def migration(self):
        '''override'''
        pass

    def setting_save_after(self, change_list):
        '''override'''
        pass

    def process_telegram_data(self, data, target=None):
        '''override'''
        pass

    def arg_to_dict(self, arg) -> dict:
        '''override'''
        return super().arg_to_dict(arg)

    def get_page(self, page_name) -> PluginPageBase:
        '''override'''
        return super().get_page(page_name)

    def get_module(self, module_name) -> PluginModuleBase:
        '''override'''
        return super().get_module(module_name)

    def process_discord_data(self, data):
        '''override'''
        pass

    def db_delete(self, day: int | str) -> int:
        '''override'''
        return super().db_delete(day)

    def start_celery(self, func: callable, on_message: callable = None, *args) -> Any:
        '''override'''
        return super().start_celery(func, on_message, *args, page=self)


class Setting(BaseModule):

    def __init__(self, plugin: PluginBase) -> None:
        super().__init__(plugin, name=SETTING)
        self.db_default = {
            SETTING_DB_VERSION: '3',
            SETTING_RCLONE_REMOTE_ADDR: 'http://172.17.0.1:5572',
            SETTING_RCLONE_REMOTE_VFS: '',
            SETTING_RCLONE_REMOTE_USER: '',
            SETTING_RCLONE_REMOTE_PASS: '',
            SETTING_RCLONE_MAPPING: '/mnt/gds:\n/home/cloud/sjva/VOD:/VOD',
            SETTING_PLEXMATE_MAX_SCAN_TIME: '60',
            SETTING_PLEXMATE_TIMEOVER_RANGE: '0~0',
            SETTING_PLEXMATE_PLEX_MAPPING: '',
            SETTING_STARTUP_EXECUTABLE: 'false',
            SETTING_STARTUP_COMMANDS: 'apt-get update',
            SETTING_STARTUP_TIMEOUT: '300',
            SETTING_STARTUP_DEPENDENCIES: SettingAider().depends(),
        }

    def migration(self):
        '''override'''
        with FRAMEWORK.app.app_context():
            current_db_ver = PLUGIN.ModelSetting.get(SETTING_DB_VERSION)
            db_file = FRAMEWORK.app.config['SQLALCHEMY_BINDS'][PLUGIN.package_name].replace('sqlite:///', '').split('?')[0]
            LOGGER.debug(f'DB 버전: {current_db_ver}')
            with sqlite3.connect(db_file) as conn:
                conn.row_factory = sqlite3.Row
                cs = conn.cursor()
                table_jobs = f'{PLUGIN.package_name}_jobs'
                # DB 볼륨 정리
                cs.execute(f'VACUUM;').fetchall()
                for ver in DB_VERSIONS[(DB_VERSIONS.index(current_db_ver)):]:
                    migrations.migrate(ver, table_jobs, cs)
                    current_db_ver = ver
                conn.commit()
                FRAMEWORK.db.session.flush()
            LOGGER.debug(f'최종 DB 버전: {current_db_ver}')
            PLUGIN.ModelSetting.set(SETTING_DB_VERSION, current_db_ver)

    def prerender(self, sub: str, req: LocalProxy) -> None:
        '''override'''
        super().prerender(sub, req)
        # yaml 파일 우선
        PLUGIN.ModelSetting.set(SETTING_STARTUP_DEPENDENCIES, SettingAider().depends())

    def get_template_args(self) -> dict[str, Any]:
        '''override'''
        args = super().get_template_args()
        args[SETTING_RCLONE_REMOTE_ADDR] = PLUGIN.ModelSetting.get(SETTING_RCLONE_REMOTE_ADDR)
        args[SETTING_RCLONE_REMOTE_VFS] = PLUGIN.ModelSetting.get(SETTING_RCLONE_REMOTE_VFS)
        args[SETTING_RCLONE_REMOTE_USER] = PLUGIN.ModelSetting.get(SETTING_RCLONE_REMOTE_USER)
        args[SETTING_RCLONE_REMOTE_PASS] = PLUGIN.ModelSetting.get(SETTING_RCLONE_REMOTE_PASS)
        args[SETTING_RCLONE_MAPPING] = PLUGIN.ModelSetting.get(SETTING_RCLONE_MAPPING)
        args[SETTING_PLEXMATE_MAX_SCAN_TIME] = PLUGIN.ModelSetting.get(SETTING_PLEXMATE_MAX_SCAN_TIME)
        args[SETTING_PLEXMATE_TIMEOVER_RANGE] = PLUGIN.ModelSetting.get(SETTING_PLEXMATE_TIMEOVER_RANGE)
        args[SETTING_PLEXMATE_PLEX_MAPPING] = PLUGIN.ModelSetting.get(SETTING_PLEXMATE_PLEX_MAPPING)
        args[SETTING_STARTUP_EXECUTABLE] = PLUGIN.ModelSetting.get(SETTING_STARTUP_EXECUTABLE)
        args[SETTING_STARTUP_COMMANDS] = PLUGIN.ModelSetting.get(SETTING_STARTUP_COMMANDS)
        args[SETTING_STARTUP_TIMEOUT] = PLUGIN.ModelSetting.get(SETTING_STARTUP_TIMEOUT)
        args[SETTING_STARTUP_DEPENDENCIES] = PLUGIN.ModelSetting.get(SETTING_STARTUP_DEPENDENCIES)
        return args

    def process_command(self, command: str, arg1: str, arg2: str, arg3: str, req: LocalProxy) -> Response:
        '''ovverride'''
        ret = {'ret':'success', 'title': 'Rclone Remote'}
        try:
            if command == 'command_test_connection':
                response = SettingAider().remote_command('vfs/list', arg1, arg2, arg3)
                if int(str(response.status_code)[0]) == 2:
                    ret['vfses'] = response.json()['vfses']
                else:
                    ret['ret'] = 'failed'
                ret['modal'] = response.text
            elif command == 'save':
                self.depends()
        except:
            tb = traceback.format_exc()
            LOGGER.error(tb)
            ret['ret'] = 'failed'
            ret['modal'] = str(tb)
        finally:
            return jsonify(ret)

    def setting_save_after(self, changes: list) -> None:
        '''override'''
        LOGGER.debug(f'변경된 설정값: {changes}')
        for change in changes:
            if change == f'{self.name}_startup_dependencies':
                SettingAider().depends(PLUGIN.ModelSetting.get(SETTING_STARTUP_DEPENDENCIES))


class Schedule(BaseModule):

    def __init__(self, plugin: PluginBase) -> None:
        super().__init__(plugin, name=SCHEDULE)
        self.db_default = {
            f'{self.name}_working_directory': '/',
            f'{self.name}_last_list_option': ''
        }
        self.web_list_model = Job

    def get_template_args(self) -> dict[str, Any]:
        '''override'''
        args = super().get_template_args()
        args[f'{self.name}_working_directory'] = PLUGIN.ModelSetting.get(SCHEDULE_WORKING_DIRECTORY)
        args[f'{self.name}_last_list_option'] = PLUGIN.ModelSetting.get(SCHEDULE_LAST_LIST_OPTION)
        args['rclone_remote_vfs'] = PLUGIN.ModelSetting.get(SETTING_RCLONE_REMOTE_VFS)
        plexmateaider = PlexmateAider()
        args['periodics'] = plexmateaider.get_periodics()
        args['sections'] = plexmateaider.get_sections()
        args['task_keys'] = TASK_KEYS
        args['tasks'] = TASKS
        args['statuses'] = STATUSES
        args['status_keys'] = STATUS_KEYS
        args['ff_schedule_keys'] = FF_SCHEDULE_KEYS
        args['ff_schedules'] = FF_SCHEDULES
        args['scan_mode_keys'] = SCAN_MODE_KEYS
        args['scan_modes'] = SCAN_MODES
        args['section_type_keys'] = SECTION_TYPE_KEYS
        args['section_types'] = SECTION_TYPES
        return args

    def process_command(self, command: str, arg1: str | None, arg2: str | None, arg3: str | None, request: LocalProxy) -> Response:
        '''override'''
        LOGGER.debug(f'요청: {command}, {arg1}, {arg2}, {arg3}')
        try:
            # 일정 리스트는 Job.web_list()
            if command == 'list':
                browseraider = BrowserAider()
                dir_list = json.dumps(browseraider.get_dir(arg1))
                PLUGIN.ModelSetting.set(SCHEDULE_WORKING_DIRECTORY, arg1)
                if dir_list:
                    result, data = True, dir_list
                else:
                    result, data = False, '폴더 목록을 생성할 수 없습니다.'
            elif command == 'save':
                job = Job.update_formdata(parse_qs(arg1))
                if job.id > 0:
                    result, data = True, '저장했습니다.'
                else:
                    result, data = False, '저장할 수 없습니다.'
            elif command == 'delete':
                if Job.delete_by_id(arg1):
                    JobAider.set_schedule(int(arg1), False)
                    result, data = True, f'삭제 했습니다: ID {arg1}'
                else:
                    result, data = False, f'삭제할 수 없습니다: ID {arg1}'
            elif command == 'execute':
                thread_func(JobAider().start_job, Job.get_job(int(arg1)))
                result, data = True, '일정을 실행헀습니다.'
            elif command == 'schedule':
                active = True if arg2.lower() == 'true' else False
                result, data = JobAider.set_schedule(int(arg1), active)
            elif command in TASK_KEYS:
                result, data = self.task_command(command, arg1, arg2, arg3)
            elif command == 'test':
                result, data = True, '테스트 작업'
            else:
                result, data = False, f'알 수 없는 명령입니다: {command}'
        except Exception as e:
            LOGGER.error(traceback.format_exc())
            result, data = False, str(e)
        finally:
            return jsonify({'success': result, 'data': data})

    def plugin_load(self) -> None:
        '''override'''
        jobs = Job.get_list()
        jobaider = JobAider()
        for job in jobs:
            if job.schedule_mode == FF_SCHEDULE_KEYS[1]:
                jobaider.start_job(job)
            elif job.schedule_mode == FF_SCHEDULE_KEYS[2] and job.schedule_auto_start:
                jobaider.add_schedule(job.id)


class Manual(BaseModule):

    def __init__(self, plugin: PluginBase) -> None:
        super().__init__(plugin, name=MANUAL)

    def get_template_args(self) -> dict[str, Any]:
        '''override'''
        args = super().get_template_args()
        with README.open() as file:
            manual = file.read()
        args['manual'] = manual
        return args


class Tool(BaseModule):

    def __init__(self, plugin: PluginBase) -> None:
        super().__init__(plugin, name=TOOL, first_menu=TOOL_TRASH)
        self.set_page_list([ToolTrash])


class ToolTrash(BasePage):

    def __init__(self, plugin: PluginBase, parent: PluginModuleBase) -> None:
        super().__init__(plugin, parent, name=TOOL_TRASH)
        self.db_default = {
            TOOL_TRASH_TASK_STATUS: STATUS_KEYS[0],
        }
        PLUGIN.ModelSetting.set(TOOL_TRASH_TASK_STATUS, STATUS_KEYS[0])


    def get_template_args(self) -> dict[str, Any]:
        '''override'''
        args = super().get_template_args()
        args['section_type_keys'] = SECTION_TYPE_KEYS
        args['section_types'] = SECTION_TYPES
        plexmateaider = PlexmateAider()
        args['sections'] = plexmateaider.get_sections()
        args['task_keys'] = TASK_KEYS
        args['tasks'] = TASKS
        args['scan_mode_keys'] = SCAN_MODE_KEYS
        args['scan_modes'] = SCAN_MODES
        args['tool_trash_keys'] = TOOL_TRASH_KEYS
        args['tool_trashes'] = TOOL_TRASHES
        args['status_keys'] = STATUS_KEYS
        args[TOOL_TRASH_TASK_STATUS.lower()] = PLUGIN.ModelSetting.get(TOOL_TRASH_TASK_STATUS)
        return args

    def process_command(self, command: str, arg1: str | None, arg2: str | None, arg3: str | None, request: LocalProxy) -> Response:
        '''override'''
        LOGGER.debug(f'요청: {command}, {arg1}, {arg2}, {arg3}')
        try:
            status = PLUGIN.ModelSetting.get(TOOL_TRASH_TASK_STATUS)
            if command == 'status':
                result, data = True, status
            elif command == 'list':
                section_id = int(arg1)
                page_no = int(arg2)
                limit = int(arg3)
                plexmateaider = PlexmateAider()
                result, data = True, plexmateaider.get_trash_list(section_id, page_no, limit)
            elif command == 'stop':
                if status == STATUS_KEYS[1] or status == STATUS_KEYS[3]:
                    PLUGIN.ModelSetting.set(TOOL_TRASH_TASK_STATUS, STATUS_KEYS[3])
                    result, data = True, "작업을 멈추는 중입니다."
                else:
                    result, data = False, "실행중이 아닙니다."
            elif status == STATUS_KEYS[0]:
                if command == 'delete':
                    metadata_id = int(arg1)
                    mediaitem_id = int(arg2)
                    result, data = True, PlexmateAider().delete_media(metadata_id, mediaitem_id)
                elif command in TASK_KEYS:
                    result, data = self.task_command(command, arg1, arg2, arg3)
                elif command in TOOL_TRASH_KEYS:
                    if status == STATUS_KEYS[0]:
                        job = Job.get_job()
                        job.task = command
                        job.section_id = int(arg1)
                        thread_func(JobAider().start_job, job)
                        result, data = True, f'작업을 실행했습니다.'
                    else:
                        result, data = False, '작업이 실행중입니다.'
                else:
                    result, data = False, f'알 수 없는 명령입니다: {command}'
            else:
                result, data = False, '작업이 실행중입니다.'
        except Exception as e:
            LOGGER.error(traceback.format_exc())
            result, data = False, str(e)
        finally:
            return jsonify({'success': result, 'data': data})
