import os
from pathlib import Path
from datetime import datetime
from typing import Any
import traceback
import shutil
import pathlib
import yaml

import requests

from framework.scheduler import Job as FrameworkJob # type: ignore

from .setup import PLUGIN, FRAMEWORK, SETTING, LOGGER
from .models import Job, TASKS, TASK_KEYS, STATUS_KEYS, FF_SCHEDULE_KEYS, SCAN_MODE_KEYS
from .agents import Agent, RcloneAgent, PlexmateAgent, UbuntuAgent


class Aider:

    def __init__(self):
        pass

    def split_by_newline(cls, setting_text: str) -> list[str]:
        return [text.strip() for text in setting_text.split('\n')]

    def _split_by_newline(cls, setting_text: str) -> list[str]:
        if '\r\n' in setting_text:
            return setting_text.split('\r\n')
        elif '\n\r' in setting_text:
            return setting_text.split('\n\r')
        elif '\r' in setting_text:
            return setting_text.split('\r')
        else:
            return setting_text.split('\n')


class JobAider(Aider):

    def __init__(self):
        super().__init__()

    def handle(self, job: Job | dict[str, Any]):
        if isinstance(job, Job):
            task = job.task
            target = job.target
            recursive = job.recursive
            vfs = job.vfs
            scan_mode = job.scan_mode
            periodic_id = job.periodic_id
            clear_type = job.clear_type
            clear_level = job.clear_level
            clear_section = job.clear_section
        else:
            task = job.get('task')
            target = job.get('target')
            recursive = job.get('recursive')
            vfs = PLUGIN.ModelSetting.get(f'{SETTING}_rclone_remote_vfs')
            scan_mode = job.get('scan_mode')
            periodic_id = job.get('periodic_id')
            clear_type = None
            clear_level = None
            clear_section = -1

        startup_executable = PLUGIN.ModelSetting.get(f'{SETTING}_startup_executable')
        startup_executable = True if startup_executable.lower() == 'true' else False

        brief = self.get_agent_brief(target, vfs, recursive, scan_mode, periodic_id, startup_executable, clear_type, clear_level, clear_section)
        agent = self.hire_agent(task, brief)

        # start task
        self.run_agent(self, agent, job)
        LOGGER.debug(f'job done...')

    @FRAMEWORK.celery.task
    def run_agent(self, agent: Agent, job: Job | dict[str, Any]) -> None:
        if isinstance(job, Job): job.set_status(STATUS_KEYS[1])
        journal = agent.run()
        if isinstance(job, Job):
            job.journal = ('\n').join(journal)
            job.set_status(STATUS_KEYS[2])

    def get_agent_brief(self, target: str, vfs: str, recursive: bool,
                        scan_mode: str, periodic_id: int, startup_executable: bool,
                        clear_type: str = None, clear_level: str = None, clear_section: int = -1) -> dict[str, Any]:
        return {
            'rclone': {
                'rc_addr': PLUGIN.ModelSetting.get(f'{SETTING}_rclone_remote_addr'),
                'rc_user': PLUGIN.ModelSetting.get(f'{SETTING}_rclone_remote_user'),
                'rc_pass': PLUGIN.ModelSetting.get(f'{SETTING}_rclone_remote_pass'),
                'rc_mapping': self.parse_mappings(PLUGIN.ModelSetting.get(f'{SETTING}_rclone_remote_mapping')),
            },
            'log': {
                'logger': LOGGER,
                'level': LOGGER.level
            },
            'args': {
                'dirs': [target],
                'fs': vfs,
                'recursive': recursive,
                'periodic_id': periodic_id,
                'scan_mode': scan_mode,
                'command': '',
                'clear_type': clear_type,
                'clear_level': clear_level,
                'clear_section': clear_section,
            },
            'init': {
                'execute_commands': startup_executable,
                'commands': self.split_by_newline(PLUGIN.ModelSetting.get(f'{SETTING}_startup_commands')),
                'timeout': int(PLUGIN.ModelSetting.get(f'{SETTING}_startup_timeout')),
                'dependencies': yaml.safe_load(SettingAider.depends()).get('dependencies'),
            },
            'plexmate': {
                'max_scan_time': int(PLUGIN.ModelSetting.get(f'{SETTING}_plexmate_max_scan_time')),
                'timeover_range': PLUGIN.ModelSetting.get(f'{SETTING}_plexmate_timeover_range'),
                'plex_mapping': self.parse_mappings(PLUGIN.ModelSetting.get(f'{SETTING}_plexmate_plex_mapping')),
            }
        }

    def hire_agent(self, task: str, brief: dict[str, Any]):
        if task == TASK_KEYS[0]:
            if brief['args']['scan_mode'] == SCAN_MODE_KEYS[0]:
                brief['args']['command'] = 'refresh'
            elif brief['args']['scan_mode'] == SCAN_MODE_KEYS[1]:
                brief['args']['command'] = 'periodic'
            elif brief['args']['scan_mode'] == SCAN_MODE_KEYS[2]:
                brief['args']['command'] = 'refresh_web'
        elif task == TASK_KEYS[1]:
            brief['args']['command'] = 'vfs/refresh'
        elif task == TASK_KEYS[2]:
            if brief['args']['scan_mode'] == SCAN_MODE_KEYS[0]:
                brief['args']['command'] = 'scan'
            elif brief['args']['scan_mode'] == SCAN_MODE_KEYS[1]:
                brief['args']['command'] = 'scan_periodic'
            elif brief['args']['scan_mode'] == SCAN_MODE_KEYS[2]:
                brief['args']['command'] = 'scan_web'
        elif task == TASK_KEYS[3]:
            brief['args']['command'] = ''
        elif task == TASK_KEYS[4]:
            brief['args']['command'] = 'clear'

        if task == TASK_KEYS[1]:
            agent = RcloneAgent(brief)
        elif task == TASK_KEYS[5]:
            agent = UbuntuAgent(brief)
        else:
            if PLUGIN.get_plex_mate():
                agent = PlexmateAgent(brief)
            else:
                raise Exception('plex_mate 플러그인을 찾을 수 없습니다.')

        return agent

    def update(self, formdata: dict[str, list]) -> tuple[bool, str]:
        try:
            _id = int(formdata.get('id')[0]) if formdata.get('id') else -1
            task = formdata.get('sch-task')[0] if formdata.get('sch-task') else TASK_KEYS[0]
            if _id == -1:
                model = Job(task)
                model.save()
            else:
                model = Job.get_by_id(_id)
                model.task = task
            desc = formdata.get('sch-description')[0] if formdata.get('sch-description') else ''
            model.desc = desc if desc != '' else f'{TASKS[model.task]["name"]}'
            model.schedule_mode = formdata.get('sch-schedule-mode')[0] if formdata.get('sch-schedule-mode') else FF_SCHEDULE_KEYS[0]
            model.schedule_interval = formdata.get('sch-schedule-interval')[0] if formdata.get('sch-schedule-interval') else '60'
            if task == TASK_KEYS[5]:
                model.target = '시작시 설정의 커맨드를 실행'
                model.schedule_interval = '매 시작'
            elif task == TASK_KEYS[3]:
                model.target = 'Plexmate의 READY 항목을 새로고침'
            else :
                model.target = formdata.get('sch-target-path')[0] if formdata.get('sch-target-path') else '/'
            model.vfs = formdata.get('sch-vfs')[0] if formdata.get('sch-vfs') else 'remote:'
            recursive = formdata.get('sch-recursive')[0] if formdata.get('sch-recursive') else 'false'
            model.recursive = True if recursive.lower() == 'true' else False
            schedule_auto_start = formdata.get('sch-schedule-auto-start')[0] if formdata.get('sch-schedule-auto-start') else 'false'
            model.schedule_auto_start = True if schedule_auto_start.lower() == 'true' else False
            model.scan_mode = formdata.get('sch-scan-mode')[0] if formdata.get('sch-scan-mode') else SCAN_MODE_KEYS[0]
            model.periodic_id = int(formdata.get('sch-scan-mode-periodic-id')[0]) if formdata.get('sch-scan-mode-periodic-id') else -1
            model.clear_type = formdata.get('sch-clear-type')[0] if formdata.get('sch-clear-type') else ''
            model.clear_level = formdata.get('sch-clear-level')[0] if formdata.get('sch-clear-level') else ''
            model.clear_section = int(formdata.get('sch-clear-section')[0]) if formdata.get('sch-clear-section') else -1
            model.save()

            schedule_id = Job.create_schedule_id(model.id)
            is_include = FRAMEWORK.scheduler.is_include(schedule_id)
            if is_include:
                FRAMEWORK.scheduler.remove_job(schedule_id)
                if model.schedule_mode == FF_SCHEDULE_KEYS[2]:
                    LOGGER.debug(f'일정에 재등록합니다: {schedule_id}')
                    self.add_schedule(model.id)

            if model.id > 0:
                result, data = True, '저장했습니다.'
            else:
                result, data = False, '저장에 실패했습니다.'
        except Exception as e:
            LOGGER.error(traceback.format_exc())
            result, data = False, '저장에 실패했습니다.'
        finally:
            return result, data

    def add_schedule(self, id: int, model: Job = None) -> bool:
        try:
            model = model if model else Job.get_by_id(id)
            schedule_id = Job.create_schedule_id(model.id)
            if not FRAMEWORK.scheduler.is_include(schedule_id):
                sch = FrameworkJob(__package__, schedule_id, model.schedule_interval, self.handle, model.desc, args=(model,))
                FRAMEWORK.scheduler.add_job_instance(sch)
            return True
        except Exception as e:
            LOGGER.error(traceback.format_exc())
            return False

    def parse_mappings(self, text: str) -> dict[str, str]:
        mappings = {}
        if text:
            settings = self.split_by_newline(text)
            for setting in settings:
                source, target = setting.split(':')
                mappings[source.strip()] = target.strip()
        return mappings


class SettingAider(Aider):

    def __init__(self):
        super().__init__()

    def remote_command(self, command: str, url: str, username: str, password: str) -> requests.Response:
        LOGGER.debug(url)
        return requests.post('{}/{}'.format(url, command), auth=(username, password))

    @classmethod
    def depends(cls, text: str = None):
        yaml_file = f'{FRAMEWORK.config["path_data"]}/db/flaskfarmaider.yaml'
        source = f'{pathlib.Path(__file__).parent.resolve()}/files/flaskfarmaider.yaml'
        try:
            if not os.path.exists(yaml_file):
                shutil.copyfile(source, yaml_file)
            if text:
                with open(yaml_file, 'w+') as file:
                    file.writelines(text)
                    depends = text
            else:
                with open(yaml_file, 'r') as file:
                    depends = ('').join(file.readlines())
            return depends
        except Exception as e:
            LOGGER.error(traceback.format_exc())
            if text: return text
            else:
                with open(source, 'r') as file:
                    return ('').join(file.readlines())


class BrowserAider(Aider):

    def __init__(self):
        super().__init__()

    def get_dir(self, target_path: str) -> list[dict[str, str]]:
        target_path = Path(target_path)
        with os.scandir(target_path) as scandirs:
            target_list = [self.pack_dir(Path(entry)) for entry in scandirs]
        target_list = sorted(target_list, key=lambda entry: (entry.get('is_file'), entry.get('name')))
        parent_pack = self.pack_dir(target_path.parent)
        parent_pack['name'] = '..'
        target_list.insert(0, parent_pack)
        return target_list

    def pack_dir(self, path_obj: Path) -> dict[str, Any]:
        stats = path_obj.stat()
        return {
            'name': path_obj.name,
            'path': str(path_obj.absolute()),
            'is_file': path_obj.is_file(),
            'size': self.format_file_size(stats.st_size),
            'ctime': self.get_readable_time(stats.st_ctime),
            'mtime': self.get_readable_time(stats.st_mtime),
        }

    def get_readable_time(self, _time: float) -> str:
        return datetime.utcfromtimestamp(_time).strftime('%b %d %H:%M')

    def format_file_size(self, size: int, decimals: int = 1, binary_system: bool =True) -> str:
        units = ['B', 'K', 'M', 'G', 'T', 'P', 'E', 'Z']
        largest_unit = 'Y'
        if binary_system:
            step = 1024
        else:
            step = 1000
        for unit in units:
            if size < step:
                return f'{size:.{decimals}f}{unit}'
            size /= step
        return f'{size:.{decimals}f}{largest_unit}'
