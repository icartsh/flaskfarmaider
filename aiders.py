import os
from pathlib import Path
from datetime import datetime
from threading import Thread
from typing import Any
import traceback
import shutil
import pathlib
import yaml

import requests

from framework.scheduler import Job as FrameworkJob # type: ignore

from .setup import P, F, SETTING
from .models import Job, TASKS, TASK_KEYS, STATUS_KEYS, FF_SCHEDULE_KEYS
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
        task = job.task if isinstance(job, Job) else job['task']
        target = job.target if isinstance(job, Job) else job['target']
        recursive = job.recursive if isinstance(job, Job) else job['recursive']
        vfs = job.vfs if isinstance(job, Job) else P.ModelSetting.get(f'{SETTING}_rclone_remote_vfs')

        startup_executable = P.ModelSetting.get(f'{SETTING}_startup_executable')
        startup_executable = True if startup_executable.lower() == 'true' else False

        brief = self.get_agent_brief(target, vfs, recursive, startup_executable)
        agent = self.hire_agent(task, brief)

        @F.celery.task
        def thread_func(agent: Agent, job: Job | dict[str, Any]) -> None:
            '''
            메소드 밖의 인스턴스를 그대로 로컬 메소드 내부에서 사용하면 매 실행시 동일한 인스턴스를 사용하게 됨
            로컬 매소드 scope 내에서 처리되도록 인스턴스를 파라미터로 받아야 함
            '''
            if isinstance(job, Job): job.set_status(STATUS_KEYS[1])
            journal = agent.run()
            if isinstance(job, Job):
                job.journal = ('\n').join(journal)
                job.set_status(STATUS_KEYS[2])
        # start task
        thread_func(agent, job)
        P.logger.debug(f'task done...')

    def schedule_func(self, *args, **kwargs):
        try:
            _id = args[0]
            job = Job.get_by_id(_id)
            self.handle(job)
        except Exception as e:
            P.logger.error(traceback.format_exc())

    def get_agent_brief(self, target: str, vfs: str, recursive: bool, startup_executable: bool) -> dict[str, Any]:
        return {
            'rclone': {
                'rc_addr': P.ModelSetting.get(f'{SETTING}_rclone_remote_addr'),
                'rc_user': P.ModelSetting.get(f'{SETTING}_rclone_remote_user'),
                'rc_pass': P.ModelSetting.get(f'{SETTING}_rclone_remote_pass'),
                'rc_mapping': self.parse_mappings(P.ModelSetting.get(f'{SETTING}_rclone_remote_mapping')),
            },
            'log': {
                'logger': P.logger,
                'level': P.logger.level
            },
            'args': {
                'dirs': [target],
                'fs': vfs,
                'recursive': recursive,
                'job_id': target,
            },
            'init': {
                'execute_commands': startup_executable,
                'commands': self.split_by_newline(P.ModelSetting.get(f'{SETTING}_startup_commands')),
                'timeout': int(P.ModelSetting.get(f'{SETTING}_startup_timeout')),
                'dependencies': yaml.safe_load(SettingAider.depends()).get('dependencies'),
            },
            'ff_config': F.config['config_filepath'],
            'plexmate': {
                'max_scan_time': int(P.ModelSetting.get(f'{SETTING}_plexmate_max_scan_time')),
                'timeover_range': P.ModelSetting.get(f'{SETTING}_plexmate_timeover_range'),
                'plex_mapping': self.parse_mappings(P.ModelSetting.get(f'{SETTING}_plexmate_plex_mapping')),
            }
        }

    def hire_agent(self, task: str, brief: dict[str, Any]):
        # task route
        if task == TASK_KEYS[0]:
            brief['args']['command'] = 'vfs/refresh'
            agent = RcloneAgent(brief)
        elif task == TASK_KEYS[1]:
            brief['args']['command'] = 'scan_web'
            agent = PlexmateAgent(brief)
        elif task == TASK_KEYS[2]:
            agent = UbuntuAgent(brief)
        elif task == TASK_KEYS[3]:
            brief['args']['command'] = 'scan'
            agent = PlexmateAgent(brief)
        elif task == TASK_KEYS[5]:
            brief['args']['command'] = 'refresh'
            agent = PlexmateAgent(brief)
        elif task == TASK_KEYS[6]:
            brief['args']['command'] = 'periodic'
            agent = PlexmateAgent(brief)
        elif task == TASK_KEYS[7]:
            brief['args']['command'] = 'refresh_web'
            agent = PlexmateAgent(brief)
        else:
            agent = PlexmateAgent(brief)
        return agent

    def update(self, formdata: dict[str, list]) -> tuple[bool, str]:
        try:
            _id = int(formdata.get('id')[0]) if formdata.get('id') else -1
            task = formdata.get('sch-task')[0] if formdata.get('sch-task') else TASK_KEYS[0]
            schedule_mode = formdata.get('sch-schedule-mode')[0] if formdata.get('sch-schedule-mode') else FF_SCHEDULE_KEYS[0]
            if _id == -1:
                model = Job(task, schedule_mode)
                model.save()
            else:
                model = Job.get_by_id(_id)
                model.schedule_mode = schedule_mode
                model.task = task
            desc = formdata.get('sch-description')[0] if formdata.get('sch-description') else ''
            model.desc = desc if desc != '' else f'{TASKS[model.task]["name"]}'
            model.commands = formdata.get('sch-commands')[0] if formdata.get('sch-commands') else ''
            model.schedule_interval = formdata.get('sch-schedule-interval')[0] if formdata.get('sch-schedule-interval') else '60'
            if task == TASK_KEYS[2]:
                model.target = '시작시 설정의 커맨드를 실행'
                model.schedule_interval = '매 시작'
            elif task == TASK_KEYS[4]:
                model.target = 'Plexmate의 READY 항목을 새로고침'
            else :
                model.target = formdata.get('sch-target-path')[0] if formdata.get('sch-target-path') else '/'
            model.vfs = formdata.get('sch-vfs', 'remote:')[0] if formdata.get('sch-vfs', 'remote:') else ''
            recursive = formdata.get('sch-recursive')[0] if formdata.get('sch-recursive') else 'false'
            model.recursive = True if recursive.lower() == 'true' else False
            schedule_auto_start = formdata.get('sch-schedule-auto-start')[0] if formdata.get('sch-schedule-auto-start') else 'false'
            model.schedule_auto_start = True if schedule_auto_start.lower() == 'true' else False
            model.save()

            if model.id:
                if _id > 0 and model.schedule_mode != FF_SCHEDULE_KEYS[2]:
                    F.scheduler.remove_job(f'{__package__}_{_id}')
                result, data = True, '저장했습니다.'
            else:
                result, data = False, '저장에 실패했습니다.'
        except Exception as e:
            P.logger.error(traceback.format_exc())
            result, data = False, '저장에 실패했습니다.'
        finally:
            return result, data

    def add_schedule(self, id: int, model: Job = None) -> bool:
        try:
            model = model if model else Job.get_by_id(id)
            schedule_id = Job.create_schedule_id(model.id)
            if not F.scheduler.is_include(schedule_id):
                sch = FrameworkJob(__package__, schedule_id, model.schedule_interval, self.schedule_func, model.desc, args=(model.id, True))
                F.scheduler.add_job_instance(sch)
            return True
        except Exception as e:
            P.logger.error(traceback.format_exc())
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
        P.logger.debug(url)
        return requests.post('{}/{}'.format(url, command), auth=(username, password))

    @classmethod
    def depends(cls, text: str = None):
        yaml_file = f'{F.config["path_data"]}/db/flaskfarmaider.yaml'
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
            P.logger.error(traceback.format_exc())
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
