import json
import traceback
from typing import Any, Callable
from urllib.parse import parse_qs

from flask import Response, render_template, jsonify # type: ignore
from werkzeug.local import LocalProxy # type: ignore

from plugin.create_plugin import PluginBase # type: ignore
from plugin.logic_module_base import PluginModuleBase # type: ignore

from .setup import FRAMEWORK, PLUGIN, SETTING, SCHEDULE, LOGGER
from .models import Job, TASK_KEYS, TASKS, STATUS_KEYS, STATUSES, FF_SCHEDULE_KEYS, FF_SCHEDULES, SCAN_MODE_KEYS, SCAN_MODES
from .aiders import BrowserAider, SettingAider, JobAider


class BaseModule(PluginModuleBase):

    def __init__(self, plugin: PluginBase, first_menu: str = None, name: str = None, scheduler_desc: str = None) -> None:
        super(BaseModule, self).__init__(plugin, name=name, scheduler_desc=scheduler_desc)
        self.db_default = {}

    def pre_rendering(func: Callable) -> Callable:
        def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            self.set_recent_menu(args[1])
            LOGGER.debug(f'rendering: {self.name}')
            result = func(self, *args, **kwargs)
            return result
        return wrapper

    # 최근 사용 메뉴 갱신
    def set_recent_menu(self, req: LocalProxy) -> None:
        current_menu = '|'.join(req.path[1:].split('/')[1:])
        LOGGER.debug(f'current_menu: {current_menu}')
        if not current_menu == PLUGIN.ModelSetting.get('recent_menu_plugin'):
            PLUGIN.ModelSetting.set('recent_menu_plugin', current_menu)

    @pre_rendering
    def process_menu(self, sub: str, req: LocalProxy) -> Response:
        try:
            try:
                # yaml 파일 우선
                PLUGIN.ModelSetting.set(f'{SETTING}_startup_dependencies', SettingAider.depends())
            except Exception as e:
                pass
            args = PLUGIN.ModelSetting.to_dict()

            plexmate = PLUGIN.get_plex_mate()
            if plexmate:
                periodics = []
                jobs = plexmate.logic.get_module('periodic').get_jobs()
                for job in jobs:
                    idx = int(job['job_id'].replace('plex_mate_periodic_', '')) + 1
                    section = job.get('섹션ID', -1)
                    section_data = plexmate.PlexDBHandle.library_section(section)
                    if section_data:
                        name = section_data.get('name')
                    else:
                        LOGGER.debug(f'skip nonexistent section: {section}')
                        continue
                    periodics.append({'idx': idx, 'section': section, 'name': name, 'desc': job.get('설명', '')})
                args['periodics'] = periodics
                sections = {
                    'movie': plexmate.PlexDBHandle.library_sections(section_type=1),
                    'show': plexmate.PlexDBHandle.library_sections(section_type=2),
                    'music': plexmate.PlexDBHandle.library_sections(section_type=8),
                }
                args['sections'] = sections
            else:
                LOGGER.warning(f'plex_mate 플러그인을 찾을 수 없습니다.')
                args['periodics'] = []
                args['sections'] = {'movie': [], 'show': [], 'music': []}
            args['module_name'] = self.name
            args['task_keys'] = TASK_KEYS
            args['tasks'] = TASKS
            args['statuses'] = STATUSES
            args['status_keys'] = STATUS_KEYS
            args['ff_schedule_keys'] = FF_SCHEDULE_KEYS
            args['ff_schedules'] = FF_SCHEDULES
            args['scan_mode_keys'] = SCAN_MODE_KEYS
            args['scan_modes'] = SCAN_MODES
            return render_template(f'{__package__}_{self.name}.html', args=args)
        except Exception as e:
            LOGGER.error(f'Exception:{str(e)}')
            LOGGER.error(traceback.format_exc())
            return render_template('sample.html', title=req.path)


class Setting(BaseModule):

    # create_plugin_instance 에서 Module(Plugin)의 형태로 생성자를 호출
    def __init__(self, plugin: PluginBase) -> None:
        super().__init__(plugin, name=SETTING)
        self.aider = SettingAider()
        self.db_default = {
            f'{self.name}_db_version': '2',
            f'{self.name}_rclone_remote_addr': 'http://172.17.0.1:5572',
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

    def migration(self):
        '''override'''
        try:
            import sqlite3
            with FRAMEWORK.app.app_context():
                db_file = FRAMEWORK.app.config['SQLALCHEMY_BINDS'][PLUGIN.package_name].replace('sqlite:///', '').split('?')[0]
                current_db_ver = PLUGIN.ModelSetting.get(f'{self.name}_db_version')
                LOGGER.debug(f'current db version: {current_db_ver}')
                connection = sqlite3.connect(db_file)
                connection.row_factory = sqlite3.Row
                cs = connection.cursor()
                table_jobs = f'{__package__}_jobs'
                if current_db_ver == '1':
                    LOGGER.debug('start migration from 1 to 2...')
                    # check old table
                    old_table_rows = cs.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='job'").fetchall()
                    if old_table_rows[0]['count(*)']:
                        LOGGER.debug('old table exists!')
                        cs.execute(f'ALTER TABLE "job" RENAME TO "job_OLD_TABLE"').fetchall()
                        new_table_rows = cs.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{table_jobs}'").fetchall()
                        if new_table_rows[0]['count(*)']:
                            # drop new blank table
                            LOGGER.debug('new blank table exists!')
                            cs.execute(f'DROP TABLE {table_jobs}').fetchall()
                        # rename table
                        cs.execute(f'ALTER TABLE "job_OLD_TABLE" RENAME TO "{table_jobs}"').fetchall()

                        # add/drop columns
                        rows = cs.execute(f'SELECT name FROM pragma_table_info("{table_jobs}")').fetchall()
                        cols = [row['name'] for row in rows]
                        if 'commands' in cols:
                            cs.execute(f'ALTER TABLE "{table_jobs}" DROP COLUMN "commands"').fetchall()
                        if 'scan_mode' not in cols:
                            cs.execute(f'ALTER TABLE "{table_jobs}" ADD COLUMN "scan_mode" VARCHAR').fetchall()
                        if 'periodic_id' not in cols:
                            cs.execute(f'ALTER TABLE "{table_jobs}" ADD COLUMN "periodic_id" INTEGER').fetchall()

                        # check before seting values
                        rows = cs.execute(f'SELECT name FROM pragma_table_info("{table_jobs}")').fetchall()
                        cols = [row['name'] for row in rows]
                        LOGGER.debug(f'table cols: {cols}')
                        rows = cs.execute(f'SELECT * FROM "{table_jobs}"').fetchall()
                        for row in rows:
                            LOGGER.debug(f"{row['id']} | {row['ctime']} | {row['task']} | {row['desc']} | {row['target']} | {row['scan_mode']} | {row['periodic_id']}")

                        LOGGER.debug('========== set values ==========')

                        # set values
                        rows = cs.execute(f'SELECT * FROM "{table_jobs}"').fetchall()
                        for row in rows:
                            if not row['scan_mode']:
                                cs.execute(f'UPDATE {table_jobs} SET scan_mode = "plexmate" WHERE id = {row["id"]}').fetchall()
                            if not row['periodic_id']:
                                cs.execute(f'UPDATE {table_jobs} SET periodic_id = -1 WHERE id = {row["id"]}').fetchall()

                            if row['task'] == 'refresh':
                                pass
                            elif row['task'] == 'scan':
                                # Plex Web API로 스캔 요청
                                cs.execute(f'UPDATE {table_jobs} SET scan_mode = "web" WHERE id = {row["id"]}').fetchall()
                            elif row['task'] == 'startup':
                                pass
                            elif row['task'] == 'pm_scan':
                                # Plexmate로 스캔 요청
                                cs.execute(f'UPDATE {table_jobs} SET task = "scan" WHERE id = {row["id"]}').fetchall()
                            elif row['task'] == 'pm_ready_refresh':
                                # Plexmate Ready 새로고침
                                pass
                            elif row['task'] == 'refresh_pm_scan':
                                # 새로고침 후 Plexmate 스캔
                                cs.execute(f'UPDATE {table_jobs} SET task = "refresh_scan" WHERE id = {row["id"]}').fetchall()
                                pass
                            elif row['task'] == 'refresh_pm_periodic':
                                # 새로고침 후 주기적 스캔
                                cs.execute(f'UPDATE {table_jobs} SET task = "refresh_scan" WHERE id = {row["id"]}').fetchall()
                                cs.execute(f'UPDATE {table_jobs} SET scan_mode = "periodic" WHERE id = {row["id"]}').fetchall()
                                cs.execute(f'UPDATE {table_jobs} SET periodic_id = {int(row["target"])} WHERE id = {row["id"]}').fetchall()
                                cs.execute(f'UPDATE {table_jobs} SET target = "" WHERE id = {row["id"]}').fetchall()
                            elif row['task'] == 'refresh_scan':
                                # 새로고침 후 웹 스캔
                                cs.execute(f'UPDATE {table_jobs} SET scan_mode = "web" WHERE id = {row["id"]}').fetchall()

                        # final check
                        rows = cs.execute(f'SELECT * FROM "{table_jobs}"').fetchall()
                        for row in rows:
                            LOGGER.debug(f"{row['id']} | {row['ctime']} | {row['task']} | {row['desc']} | {row['target']} | {row['scan_mode']} | {row['periodic_id']}")
                            #print(dict(row))
                            if not row['task'] in TASK_KEYS:
                                LOGGER.error(f'wrong task: {row["task"]}')
                            if not row['scan_mode'] in SCAN_MODE_KEYS:
                                LOGGER.error(f'wrong scan_mode: {row["scan_mode"]}')
                    PLUGIN.ModelSetting.set(f'{self.name}_db_version', '2')
                elif current_db_ver == '2':
                    LOGGER.debug('start migration from 2 to 3...')
                    rows = cs.execute(f'SELECT name FROM pragma_table_info("{table_jobs}")').fetchall()
                    cols = [row['name'] for row in rows]
                    if 'clear_type' not in cols:
                        cs.execute(f'ALTER TABLE "{table_jobs}" ADD COLUMN "clear_type" VARCHAR').fetchall()
                    if 'clear_level' not in cols:
                        cs.execute(f'ALTER TABLE "{table_jobs}" ADD COLUMN "clear_level" VARCHAR').fetchall()
                    if 'clear_section' not in cols:
                        cs.execute(f'ALTER TABLE "{table_jobs}" ADD COLUMN "clear_section" INTEGER').fetchall()
                    PLUGIN.ModelSetting.set(f'{self.name}_db_version', '3')
                connection.commit()
                FRAMEWORK.db.session.flush()
                connection.close()
        except Exception as e:
            LOGGER.error(f'Exception:{str(e)}')
            LOGGER.error(traceback.format_exc())

    def process_command(self, command: str, arg1: str, arg2: str, arg3: str, req: LocalProxy) -> Response:
        '''ovverride'''
        ret = {'ret':'success', 'title': 'Rclone Remote'}
        LOGGER.debug('command: %s' % command)
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
            LOGGER.error(f'Exception:{str(e)}')
            LOGGER.error(traceback.format_exc())
            ret['ret'] = 'failed'
            ret['modal'] = str(traceback.format_exc())
            return jsonify(ret)
        return jsonify(ret)

    def setting_save_after(self, changes: list) -> None:
        '''override'''
        LOGGER.debug(f'setting saved: {changes}')
        for change in changes:
            if change == f'{self.name}_startup_dependencies':
                SettingAider.depends(PLUGIN.ModelSetting.get(f'{SETTING}_startup_dependencies'))


class Schedule(BaseModule):

    def __init__(self, plugin: PluginBase) -> None:
        super().__init__(plugin, name=SCHEDULE)
        self.db_default = {
            f'{self.name}_working_directory': '/',
            f'{self.name}_last_list_option': ''
        }
        self.browseraider = BrowserAider()
        self.jobaider = JobAider()
        self.web_list_model = Job

    def process_command(self, command: str, arg1: str | None, arg2: str | None, arg3: str | None, request: LocalProxy) -> Response:
        LOGGER.debug(f'process_command: {command}, {arg1}, {arg2}, {arg3}')
        try:
            if command == 'list':
                dir_list = json.dumps(self.browseraider.get_dir(arg1))
                PLUGIN.ModelSetting.set(f'{self.name}_working_directory', arg1)
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
                if arg3:
                    scan_mode, periodic_id = arg3.split('|')
                else:
                    scan_mode = SCAN_MODE_KEYS[0]
                    periodic_id = '-1'

                if arg1:
                    job = {
                        'task': command,
                        'target': arg1,
                        'recursive': recursive,
                        'scan_mode': scan_mode,
                        'periodic_id': int(periodic_id) if periodic_id else -1,
                    }
                    LOGGER.debug(f'process_command: {job}')
                    self.jobaider.handle(job)
                    result, data = True, '작업이 종료되었습니다.'
                else:
                    result, data = False, f'경로 정보가 없습니다.'
            else:
                result, data = False, f'알 수 없는 명령입니다: {command}'
        except Exception as e:
            LOGGER.error(traceback.format_exc())
            result, data = False, str(e)
        finally:
            return jsonify({'success': result, 'data': data})

    def set_schedule(self, job_id: int | str, active: bool = False) -> tuple[bool, str]:
        schedule_id = Job.create_schedule_id(int(job_id))
        is_include = FRAMEWORK.scheduler.is_include(schedule_id)
        if active and is_include:
            result, data = False, f'이미 일정에 등록되어 있습니다.'
        elif active and not is_include:
            result = self.jobaider.add_schedule(job_id)
            data = '일정에 등록했습니다.' if result else '일정에 등록하지 못했어요.'
        elif not active and is_include:
            result, data = FRAMEWORK.scheduler.remove_job(schedule_id), '일정에서 제외했습니다.'
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
