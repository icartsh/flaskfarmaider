import json
import traceback
from typing import Any, Callable
from urllib.parse import parse_qs

from flask import Response, render_template, jsonify # type: ignore
from werkzeug.local import LocalProxy # type: ignore

from plugin.create_plugin import PluginBase # type: ignore
from plugin.logic_module_base import PluginModuleBase # type: ignore

from .setup import F, P, SETTING, SCHEDULE
from .models import Job, TASK_KEYS, TASKS, STATUS_KEYS, STATUSES, FF_SCHEDULE_KEYS, FF_SCHEDULES
from .aiders import BrowserAider, SettingAider, JobAider


class BaseModule(PluginModuleBase):

    def __init__(self, P, first_menu: str = None, name: str = None, scheduler_desc: str = None) -> None:
        super(BaseModule, self).__init__(P, name=name, scheduler_desc=scheduler_desc)
        self.db_default = {}

    def pre_rendering(func: Callable) -> Callable:
        def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            self.set_recent_menu(args[1])
            P.logger.debug(f'rendering: {self.name}')
            result = func(self, *args, **kwargs)
            return result
        return wrapper

    # 최근 사용 메뉴 갱신
    def set_recent_menu(self, req: LocalProxy) -> None:
        current_menu = '|'.join(req.path[1:].split('/')[1:])
        P.logger.debug(f'current_menu: {current_menu}')
        if not current_menu == P.ModelSetting.get('recent_menu_plugin'):
            P.ModelSetting.set('recent_menu_plugin', current_menu)

    @pre_rendering
    def process_menu(self, sub: str, req: LocalProxy) -> Response:
        try:
            try:
                # yaml 파일 우선
                P.ModelSetting.set(f'{SETTING}_startup_dependencies', SettingAider.depends())
            except Exception as e:
                pass
            args = P.ModelSetting.to_dict()
            args['module_name'] = self.name
            args['task_keys'] = TASK_KEYS
            args['tasks'] = TASKS
            args['statuses'] = STATUSES
            args['status_keys'] = STATUS_KEYS
            args['ff_schedule_keys'] = FF_SCHEDULE_KEYS
            args['ff_schedules'] = FF_SCHEDULES
            return render_template(f'{__package__}_{self.name}.html', args=args)
        except Exception as e:
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())
            return render_template('sample.html', title=req.path)


class Setting(BaseModule):

    # create_plugin_instance 에서 Module(Plugin)의 형태로 생성자를 호출
    def __init__(self, P: PluginBase) -> None:
        super().__init__(P, name=SETTING)
        self.aider = SettingAider()
        self.db_default = {
            f'{self.name}_db_version': '1',
            f'{self.name}_rclone_remote_addr': 'http://172.17.0.1:5574',
            f'{self.name}_rclone_remote_vfs': '',
            f'{self.name}_rclone_remote_user': '',
            f'{self.name}_rclone_remote_pass': '',
            f'{self.name}_rclone_remote_mapping': '/mnt/gds:\n/home/cloud/sjva/VOD:/VOD',
            f'{self.name}_plexmate_max_scan_time': '60',
            f'{self.name}_plexmate_timeover_range': '0~0',
            f'{self.name}_plexmate_plex_mapping': '',
            f'{self.name}_startup_executable': 'false',
            f'{self.name}_startup_commands': 'apt-get update',
            f'{self.name}_startup_timeout': '300',
            f'{self.name}_startup_dependencies': SettingAider.depends(),
        }

    """
    def migration(self):
        '''override'''
        try:
            with F.app.app_context():
                import sqlite3
                db_file = F.app.config['SQLALCHEMY_BINDS'][P.package_name].replace('sqlite:///', '').split('?')[0]
                P.logger.debug(db_file)
                if P.ModelSetting.get(f'{self.name}_db_version') == '1':
                    P.logger.debug('migration!!!!!!!!!!!!')
                    connection = sqlite3.connect(db_file)
                    cursor = connection.cursor()
                    query = f'ALTER TABLE task ADD vfs VARCHAR'
                    cursor.execute(query)
                    connection.close()
                    P.ModelSetting.set(f'{self.name}_db_version', '2')
                    F.db.session.flush()
        except Exception as e:
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())
    """

    def process_command(self, command: str, arg1: str, arg2: str, arg3: str, req: LocalProxy) -> Response:
        '''ovverride'''
        ret = {'ret':'success', 'title': 'Rclone Remote'}
        P.logger.debug('command: %s' % command)
        try:
            if command == 'command_test_connection':
                response = self.aider.remote_command('vfs/list', arg1, arg2, arg3)
                if int(str(response.status_code)[0]) == 2:
                    ret['vfses'] = response.json()['vfses']
                else:
                    ret['ret'] = 'failed'
                ret['modal'] = response.text
            elif command == 'save':
                self.depends()
        except Exception as e:
            P.logger.error(f'Exception:{str(e)}')
            P.logger.error(traceback.format_exc())
            ret['ret'] = 'failed'
            ret['modal'] = str(traceback.format_exc())
            return jsonify(ret)
        return jsonify(ret)

    def setting_save_after(self, changes: list) -> None:
        '''override'''
        P.logger.debug(f'setting saved: {changes}')
        for change in changes:
            if change == f'{self.name}_startup_dependencies':
                SettingAider.depends(P.ModelSetting.get(f'{SETTING}_startup_dependencies'))


class Schedule(BaseModule):

    def __init__(self, P: PluginBase) -> None:
        super().__init__(P, name=SCHEDULE)
        self.db_default = {
            f'{self.name}_working_directory': '/',
            f'{self.name}_last_list_option': ''
        }
        self.browseraider = BrowserAider()
        self.jobaider = JobAider()
        self.web_list_model = Job

    def process_command(self, command: str, arg1: str | None, arg2: str | None, arg3: str | None, request: LocalProxy) -> Response:
        P.logger.debug(f'process_command: {command}, {arg1}, {arg2}, {arg3}')
        try:
            if command == 'list':
                dir_list = json.dumps(self.browseraider.get_dir(arg1))
                P.ModelSetting.set(f'{self.name}_working_directory', arg1)
                result, data = True, dir_list
            elif command == 'save':
                result, data = self.jobaider.update(parse_qs(arg1))
            elif command == 'delete':
                if Job.delete_by_id(arg1):
                    result, data = True, f'삭제했습니다: ID {arg1}'
                    self.set_schedule(arg1, False)
                else:
                    result, data = False, f'삭제 실패: ID {arg1}'
            elif command == 'execute':
                job = Job.get_by_id(arg1)
                self.jobaider.handle(job)
                result, data = True, '실행을 완료했습니다.'
            elif command == 'schedule':
                active = True if arg2.lower() == 'true' else False
                result, data = self.set_schedule(arg1, active)
            elif command in TASK_KEYS:
                if arg2:
                    recursive = True if arg2.lower() == 'true' else False
                else:
                    recursive = False

                if arg1:
                    job = {
                        'task': command,
                        'target': arg1,
                        'commands': arg3,
                        'recursive': recursive,
                    }
                    P.logger.debug(f'process_command: {job}')
                    self.jobaider.handle(job)
                    result, data = True, '작업이 종료되었습니다.'
                else:
                    result, data = False, f'경로 정보가 없습니다.'
            else:
                result, data = False, f'알 수 없는 명령입니다: {command}'
        except Exception as e:
            P.logger.error(traceback.format_exc())
            result, data = False, str(e)
        finally:
            return jsonify({'success': result, 'data': data})

    def set_schedule(self, job_id: int | str, active: bool = False) -> tuple[bool, str]:
        schedule_id = Job.create_schedule_id(int(job_id))
        is_include = F.scheduler.is_include(schedule_id)
        if active and is_include:
            result, data = False, f'이미 일정에 등록되어 있습니다.'
        elif active and not is_include:
            result = self.jobaider.add_schedule(job_id)
            data = '일정에 등록했습니다.' if result else '일정에 등록하지 못했어요.'
        elif not active and is_include:
            result, data = F.scheduler.remove_job(schedule_id), '일정에서 제외했습니다.'
        else:
            result, data = False, '등록되지 않은 일정입니다.'
        return result, data

    def plugin_load(self) -> None:
        '''override'''
        models = Job.get_list()
        for model in models:
            if model.schedule_mode == FF_SCHEDULE_KEYS[1]:
                self.jobaider.handle(model)
            elif model.schedule_mode == FF_SCHEDULE_KEYS[2] and model.schedule_auto_start:
                self.jobaider.add_schedule(model.id)
