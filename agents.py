#!/usr/bin/env python3
import sys
import os
import logging
import traceback
import argparse
import subprocess
import yaml
import time
import base64
import shlex
from datetime import datetime

import requests


'''
Classes
'''


class AgentConfig(dict):

    def __init__(self, config):
        '''config: dict'''
        super(AgentConfig, self).__init__(config)
        for k, v in config.items():
            self.__setattr__(k, v)

    def __setitem__(self, key, value):
        '''key: str, value: Any -> None'''
        self.__setattr__(key, value)

    def __delitem__(self, key):
        '''key: str -> None'''
        super(AgentConfig, self).__delitem__(key)
        super(AgentConfig, self).__delattr__(key)

    def __setattr__(self, name, value):
        '''name: str, value: Any -> None'''
        super(AgentConfig, self).__setitem__(name, value)
        if isinstance(value, dict):
            super(AgentConfig, self).__setattr__(name, AgentConfig(value))
        else:
            super(AgentConfig, self).__setattr__(name, value)

    def __delattr__(self, name):
        '''name: str -> None'''
        super(AgentConfig, self).__delattr__(name)
        super(AgentConfig, self).__delitem__(name)

    def update(self, *args, **kwargs):
        super(AgentConfig, self).update(*args, **kwargs)
        if args:
            for arg in args:
                for k, v in arg.items():
                    self.__setattr__(k, v)
        if kwargs:
            for k, v in kwargs.items():
                self.__setattr__(k, v)


class Agent:

    name = None
    logger = None
    journal = None
    config = AgentConfig(
        {
            'log': {
                'level': 'INFO',
                'logger': None
            },
            'ff_config': '/data/config.yaml',
            'rclone': {
                'rc_addr': 'http://172.17.0.1:5572',
                'rc_user': '',
                'rc_pass': '',
                'rc_mapping': {}
            },
            'plexmate': {
                'max_scan_time': 10,
                'timeover_range': '0~0',
                'plex_mapping': {}
            },
            'init': {
                'execute_commands': False,
                'commands': [],
                'timeout': 100,
                'dependencies': {}
            },
            'args': argparse.Namespace()
        }
    )

    def __init__(self, config=None, name=None):
        '''config: dict = None, name: str = None'''
        self.name = name
        if config: self.set_config(config)
        if self.config.log.logger:
            self.logger = self.config.log.logger
        else:
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(self.config.log.level)
            self.logger.addHandler(logging.StreamHandler())
            self.config.log.logger = self.logger
        self.operations = {
            'default': self.operation_default
        }
        self.journals = []

    def journal(self, msg):
        self.journals.append(msg)
        return msg

    def set_config(self, config):
        '''config: dict -> None'''
        if 'args' in config:
            if isinstance(config['args'], argparse.Namespace):
                config['args'] = vars(config['args'])
            if config['args'].get('dirs'):
                for i, dir in enumerate(config['args']['dirs']):
                    # strip leading/tailing quotes
                    dir = dir.strip('"').strip("'") if dir else dir
                    try:
                        # decode if dir is encoded in base64
                        config['args']['dirs'][i] = str(base64.b64decode(bytes(dir, 'utf-8'), validate=True), 'utf-8')
                    except Exception as e:
                        config['args']['dirs'][i] = dir
                self.targets = config['args']['dirs']
            else:
                self.targets = None
        self.config.update(config)

    def request(self, url, method='POST', data=None, **kwargs):
        '''url: str, method: str = 'POST', data: dict = None, kwargs: dict[str, Any] -> Response'''
        try:
            if method.upper() == 'JSON':
                return requests.request('POST', url, json=data if data else {}, **kwargs)
            else:
                return requests.request(method, url, data=data, **kwargs)
        except Exception:
            tb = traceback.format_exc()
            self.logger.error(tb)
            response = requests.Response()
            response._content = bytes(tb, 'utf-8')
            response.status_code = 0
            return response

    def log_response(self, response):
        '''respnse: Response -> None'''
        try:
            msg = f'code: {response.status_code}, content: {response.json()}'
        except requests.exceptions.JSONDecodeError as jsonerr:
            msg = f'code: {response.status_code}, content: {response.text}'
        self.logger.info(self.journal(msg))

    def deduplicate(self, items):
        '''items: list[str] -> list[str]'''
        bucket = {}
        for item in items:
            bucket[item] = False
        return list(bucket.keys())

    def operation_default(self):
        pass

    def operate(self, command):
        '''command: str = None -> None'''
        self.operations.get(command, self.operation_default)()

    def run(self) -> list[str]:
        '''None -> None'''
        try:
            if hasattr(self.config.args, 'command'):
                self.operate(self.config.args.command)
            else:
                self.operate('default')
        except Exception as e:
            self.logger.error(traceback.format_exc())
            self.journal(str(e))
        return self.journals


class PluginAgent(Agent):

    def __init__(self, config, name=None):
        '''config: dict | AgentConfig, name: str = None'''
        super().__init__(config, name=name)
        from framework.init_main import Framework # type: ignore
        self.F = Framework.get_instance()

    def get_plugin(self, name):
        '''name: str -> PluginBase'''
        return self.F.PluginManager.get_plugin_instance(name)

    def get_module(self, plugin, module):
        '''plugin: str, module: str -> PluginModuleBase'''
        plugin_instance = self.get_plugin(plugin)
        return plugin_instance.logic.get_module(module)


class PlexmateAgent(PluginAgent):

    def __init__(self, config):
        '''config: dict | AgentConfig'''
        super().__init__(config, name='agent.plexmate')
        # from .plex_web import PlexWebHandle # type: ignore
        # self.plex = PlexWebHandle
        self.P = self.get_plugin('plex_mate')
        # --dirs 옵션 우선
        if not self.targets and hasattr(self.config.args, 'sections'):
            self.targets = []
            for _id in self.config.args.sections:
                self.targets += self.get_locations_by_id(_id)
        self.operations.update(
            {
                'scan': self.operation_scan,
                'refresh': self.operation_refresh,
                'periodic': self.operation_periodic,
                'scan_web': self.operation_scan_web,
                'refresh_web': self.operation_refresh_web,
            }
        )

        # http://[PMS_IP_ADDRESS]:32400/library/sections/29/refresh?path=/Users/plexuser/Movies/Media/Movies/1080p&X-Plex-Token=YourTokenGoesHere
        self.plex = {
            'url': self.P.ModelSetting.get('base_url'),
            'token': self.P.ModelSetting.get('base_token'),
            'refresh_url': '%s/library/sections/%d/refresh?X-Plex-Token=%s',
            'db': self.get_plugin('plex_mate').PlexDBHandle,
        }

    def get_scan_items(self, status):
        '''status: str -> list[ModelScanItem]'''
        return self.get_scan_model().get_list_by_status(status)

    def get_scan_targets(self, status):
        '''status: str -> list[str]'''
        targets = [scan_item.target for scan_item in self.get_scan_items(status)]
        return self.deduplicate(targets)

    def get_module(self, module):
        '''module: str -> PluginModuleBase'''
        return self.P.logic.get_module(module)

    def get_scan_model(self):
        '''None -> ModelScanItem'''
        return self.get_module('scan').web_list_model

    def check_scanning(self, max_scan_time):
        '''max_scan_time: int -> None'''
        '''
        SCANNING 항목 점검.

        PLEX_MATE에서 특정 폴더가 비정상적으로 계속 SCANNING 상태이면 이후 동일 폴더에 대한 스캔 요청이 모두 무시됨.
        예를 들어 .plexignore 가 있는 폴더는 PLEX_MATE 입장에서 스캔이 정상 종료되지 않기 때문에 해당 파일의 상태가 계속 SCANNING 으로 남게 됨.
        이 상태에서 동일한 폴더에 위치한 다른 파일이 스캔에 추가되면 스캔을 시도하지 않고 FINISH_ALREADY_IN_QUEUE 로 종료됨.

        ModelScanItem.queue_list가 현재 스캔중인 아이템의 MODEL 객체가 담겨있는 LIST임.
        클래스 변수라서 스크립트로 리스트의 내용을 조작해 보려고 시도했으나
        런타임 중 plex_mate.task_scan.Task.filecheck_thread_function() 에서 참조하는 ModelScanItem 과
        외부 스크립트에서 참조하는 ModelScanItem 의 메모리 주소가 다름을 확인함.
        flask의 app_context, celery의 Task 데코레이터, 다른 플러그인에서 접근을 해 보았지만 효과가 없었음.
        그래서 외부에서 접근한 ModelScanItem.queue_list는 항상 비어 있는 상태임.

        런타임 queue_list에서 스캔 오류 아이템을 제외시키기 위해 편법을 사용함.

        - 스캔 오류라고 판단된 item을 db에서 삭제하고 동일한 id로 새로운 item을 db에 생성
        - ModelScanItem.queue_list에는 기존 item의 객체가 아직 남아 있음.
        - 다음 파일체크 단계에서 queue_list에 남아있는 기존 item 정보로 인해 새로운 item의 STATUS가 FINISH_ALREADY_IN_QUEUE로 변경됨.
        - FINISH_* 상태가 되면 ModelScanItem.remove_in_queue()가 호출됨.
        - 새로운 item 객체는 기존 item 객체의 id를 가지고 있기 때문에 queue_list에서 기존 item 객체가 제외됨.

        주의: 계속 SCANNING 상태로 유지되는 항목은 확인 후 조치.
        '''
        model = self.get_scan_model()
        scans = self.get_scan_items('SCANNING')
        if scans:
            for scan in scans:
                if int((datetime.now() - scan.process_start_time).total_seconds() / 60) >= max_scan_time:
                    self.logger.warn(self.journal(f'스캔 시간 {max_scan_time}분 초과: {scan.target}'))
                    self.logger.warn(self.journal(f'스캔 QUEUE에서 제외: {scan.target}'))
                    model.delete_by_id(scan.id)
                    new_item = model(scan.target)
                    new_item.id = scan.id
                    new_item.save()

    def check_timeover(self, item_range):
        '''item_range: str -> None'''
        '''
        FINISH_TIMEOVER 항목 점검
        ID가 item_range 범위 안에 있는 TIMEOVER 항목들을 다시 READY 로 변경
        주의: 계속 시간 초과로 뜨는 항목은 확인 후 수동으로 조치
        '''
        overs = self.get_scan_items('FINISH_TIMEOVER')
        if overs:
            start_id, end_id = list(map(int, item_range.split('~')))
            for over in overs:
                if over.id in range(start_id, end_id + 1):
                    self.logger.warn(self.journal(f'READY 로 상태 변경: {over.id} {over.target}'))
                    over.set_status('READY', save=True)

    def get_plex_path(self, local_path):
        '''local_path: str -> str'''
        for k, v in self.config.plexmate.plex_mapping.items():
            local_path = os.path.normpath(local_path.replace(k, v))
        return local_path

    def add_scan(self, target, web=False):
        '''target: str, web: bool = False -> ModelScanItem | None'''
        if web:
            target = self.get_plex_path(target)
            items = self.plex['db'].select('SELECT library_section_id, root_path FROM section_locations')
            founds = set()
            for item in items:
                root = item['root_path']
                longer = target if len(target) >= len(root) else root
                shorter = target if len(target) < len(root) else root
                if longer.startswith(shorter):
                    founds.add(int(item['library_section_id']))
            if founds:
                self.logger.debug(self.journal(f'section ID found: [{target}] in {founds}'))
                for library in founds:
                    url = self.plex['refresh_url'] % (self.plex['url'], library, self.plex['token'])
                    url = f'{url}&path={target}'
                    response = requests.request('GET', url)
                    self.logger.debug(self.journal(f'library id: {library}, status code: {response.status_code}'))
            else:
                self.logger.error(self.journal('섹션 ID를 찾을 수 없습니다: {target}'))
            return
        else:
            scan_item = self.get_scan_model()(target)
            scan_item.save()
            self.logger.info(self.journal(f'스캔 ID: {scan_item.id}'))
            return scan_item

    def add_scans(self, targets):
        '''target: list[str] -> list[ModelScanItem]'''
        return [self.add_scan(target) for target in targets]

    def rclone_refresh(self, targets):
        '''targets: list[str] -> Generator[tuple[str, str]]'''
        rclone = RcloneAgent(self.config)
        for target in targets:
            try:
                response = rclone.vfs_refresh(target)
                result, reason = rclone.is_successful(response)
                if result:
                    reason = None
            except Exception as e:
                reason = str(e)
            if reason:
                self.logger.error(self.journal(f'새로고침 실패: [{target}]: {reason}'))
            self.journals.extend(rclone.journals)
            rclone.journals = []
            yield target, reason

    def get_locations_by_id(self, section_id):
        '''section_id: int -> list[str]'''
        plex_db = self.get_plugin('plex_mate').PlexDBHandle
        return [location.get('root_path') for location in plex_db.section_location(library_id=section_id)]

    def operation_scan(self):
        '''None -> None'''
        '''
        plexmate scan --dirs "/path/to/be/scanned"
        plexmate scan --sect 1 2 3
        단순히 스캔만 실행할 경우 사용.
        이미 vfs/refresh 되어 있으나 스캔이 누락된 경우 등..
        '''
        if self.targets:
            self.add_scans(self.targets)
        else:
            self.logger.info(self.journal('스캔 대상이 없어요.'))


    def operation_scan_web(self):
        if self.targets:
            self.add_scan(self.targets[0], True)

    def operation_default(self):
        '''None -> None'''
        '''
        plexmate [--fs remote_name:] [--recursive]
        command가 없을 경우 다음의 작업을 함
            - 스캐닝 시간을 초과한 항목을 처리
            - 파일 체크 TIMEOVER 항목을 처리
            - READY 상태의 항목을 vfs/refresh
        '''
        self.check_scanning(self.config.plexmate.max_scan_time)
        self.check_timeover(self.config.plexmate.timeover_range)
        self.targets = self.get_scan_targets('READY')
        if self.targets:
            [t for t, _ in self.rclone_refresh(self.targets)]
        else:
            self.logger.info(self.journal('새로고침 대상이 없어요.'))

    def operation_refresh(self):
        '''None -> None'''
        '''
        plexmate refresh --dirs "/path/to/be/scanned" [--fs remote_name:] [--recursive]
        plexmate refresh --sect 1 2 3 [--fs remote_name:] [--recursive]
        이미 존재하는 폴더를 vfs/refresh 한 뒤 스캔할 때 사용.
        이미 존재하는 폴더를 PLEX_MATE에 스캔 요청하면 파일 체크 주기에 따라서 vfs/refresh가 완료되기 전에 스캔이 실행 됨.
        vfs/refresh가 완료된 후 스캔을 추가할 필요가 있음.
        '''
        if self.targets:
            for target, reason in self.rclone_refresh(self.targets):
                self.add_scan(target)
        else:
            self.logger.info(self.journal('새로고침 대상이 없어요.'))

    def operation_refresh_web(self):
        if self.targets:
            for target, reason in self.rclone_refresh(self.targets):
                self.add_scan(target, True)

    def operation_periodic(self):
        '''None -> None'''
        '''
        plexmate periodic {job id} [--fs remote_name:] [--recursive]
        주기적 스캔의 작업 ID 를 입력받아 vfs/refresh를 한 뒤 주기적 스캔을 실행
        '''
        mod = self.get_module('periodic')
        if hasattr(self.config.args, 'job_id'):
            job_id = int(self.config.args.job_id) - 1
        else:
            job_id = None
        try:
            job = mod.get_jobs()[job_id]
        except IndexError as e:
            self.logger.error(self.journal(str(e)))
            job = None
        if job:
            if job.get('폴더'):
                self.targets = list(job.get('폴더'))
            else:
                self.targets = self.get_locations_by_id(job.get('섹션ID'))
            if self.targets:
                [t for t, _ in self.rclone_refresh(self.targets)]
                self.logger.info(self.journal(f'주기적 스캔 실행: {job}'))
                mod.one_execute(job_id)
            else:
                self.logger.info(self.journal('새로고침 대상이 없어요.'))
        else:
            self.logger.error(self.journal('주기적 스캔 작업을 찾을 수 없어요.'))


class RcloneAgent(Agent):

    vfses = None

    def __init__(self, config):
        '''config: dict | AgentConfig'''
        super().__init__(config, name='agent.rclone')
        self.operations.update(
            {
                'vfs/refresh': self.operation_vfs_refresh,
                'vfs/list': self.operation_vfs_list,
            }
        )
        # recursive 기본값 세팅
        if not hasattr(self.config.args, 'recursive') or self.config.args.recursive is None:
            self.config.args.recursive = False
        if not hasattr(self.config.args, 'fs') or self.config.args.fs is None:
            self.config.args.fs = self.vfses[0]

    def check_connection(self):
        '''None -> bool'''
        response = self.command('core/version')
        if int(str(response.status_code)[0]) == 2:
            self.vfses = self.command('vfs/list').json().get('vfses')
            return True
        else:
            self.vfses = ['remote:']
            self.log_response(response)
            return False

    def command(self, command, data=None):
        '''command: str, data: dict = None -> Response'''
        self.logger.debug(self.journal(f'command: {command}, parameters: {data}'))
        return self.request(
            f'{self.config.rclone.rc_addr}/{command}',
            method="JSON",
            data=data,
            auth=(self.config.rclone.rc_user, self.config.rclone.rc_pass)
        )

    def get_metadata_cache(self, fs):
        '''fs: str -> dict[str, Any]'''
        return self.vfs_stats(fs).json().get("metadataCache")

    def vfs_stats(self, fs):
        '''fs: str -> Response'''
        return self.command("vfs/stats", data={"fs": fs})

    def _vfs_refresh(self, remote_path, recursive=None, fs=None):
        '''remote_path: str, recursive: bool = None, fs: str = None -> Response'''
        data = {
            'recursive': str(recursive).lower() if recursive is not None else str(self.config.args.recursive).lower(),
            'fs': fs if fs is not None else self.config.args.fs,
            'dir': remote_path
        }
        self.logger.debug(self.journal(f'새로고침 전: {self.get_metadata_cache(data["fs"])}'))
        response = self.command('vfs/refresh', data=data)
        self.log_response(response)
        self.logger.debug(self.journal(f'새로고침 후: {self.get_metadata_cache(data["fs"])}'))
        return response

    def vfs_refresh(self, local_path):
        '''local_path: str -> Response'''
        # 이미 존재하는 파일이면 패스, 존재하지 않은 파일/폴더, 존재하는 폴더이면 진행
        if os.path.isfile(local_path):
            response = requests.Response()
            response.status_code = 0
            reason = 'already exists'
            response._content = bytes(reason, 'utf-8')
            self.logger.debug(f'{reason}: {local_path}')
        else:
            # vfs/refresh 용 존재하는 경로 찾기
            test_dirs = [local_path]
            while not os.path.exists(test_dirs[-1]):
                test_dirs.append(os.path.split(test_dirs[-1])[0])
            self.logger.debug(f"testing: {test_dirs}")
            already_exists = True if len(test_dirs) < 2 else False
            while test_dirs:
                response = self._vfs_refresh(self.get_remote_path(test_dirs[-1]))
                if os.path.exists(local_path):
                    self.logger.debug(f'EXISTS: {local_path}')
                    # 존재하지 않았던 폴더면 vfs/refresh
                    if not os.path.isfile(local_path) and not already_exists:
                        self.logger.debug(f'is already exists? : {already_exists}')
                        self._vfs_refresh(self.get_remote_path(local_path))
                        # 새로운 폴더를 새로고침 후 한번 더 타겟 경로 존재 점검
                        if not os.path.exists(local_path): continue
                    break
                else:
                    result, reason = self.is_successful(response)
                    if not result:
                        self.logger.error(self.journal(f'can not refresh: {reason}: {test_dirs[-1]}'))
                        break
                    self.logger.debug(f'still not exists...')
                test_dirs.pop()
        return response

    def is_successful(self, response):
        if not str(response.status_code).startswith('2'):
            return False, f'status code: {response.status_code}'
        try:
            # {'error': '', ...}
            # {'result': {'/path/to': 'Invalid...'}}
            # {'result': {'/path/to': 'OK'}}
            _json = response.json()
            if _json.get('result'):
                result = list(_json.get('result').values())[0]
                if result == 'OK':
                    return True, result
                else:
                    return False, result
            else:
                return False, _json.get('error')
        except Exception as e:
            self.logger.error(self.journal(str(e)))
            return False, response.text

    def operations_list(self, fs, remote, opts=None):
        '''dir: str, opts: dict[str, str] -> Response'''
        self.logger.debug(f'opts: {opts}')
        data = {
            'fs': fs,
            'remote': remote,
            'opt': opts
        }
        return self.command('operations/list', data=data)

    def get_remote_path(self, local_path):
        '''local_path: str -> str'''
        for k, v in self.config.rclone.rc_mapping.items():
            local_path = os.path.normpath(local_path.replace(k, v))
        return local_path

    def operation_default(self):
        '''None -> None'''
        '''
        rclone
        rclone 리모트에 options/get 명령을 전송
        '''
        print(self.command('options/get').text)

    def operation_vfs_refresh(self):
        '''None -> None'''
        '''
        rclone vfs/refresh --dirs "/path/to/be/refresh" [--fs remote_name:] [--recursive]
        rclone 리모트에 vfs/refresh 명령을 전송
        '''
        if self.targets:
            for target in self.targets:
                self.vfs_refresh(target)
        else:
            self.logger.info('새로고침 대상이 없어요.')

    def operation_vfs_list(self):
        '''None -> None'''
        '''
        rclone vfs/list
        rclone 리모트에 vfs/list 명령을 전송
        '''
        print(self.command('vfs/list').text)


class InitAgent(Agent):

    plugins_indtalled = None
    plugins_dir = None

    def __init__(self, config, name=None):
        '''config: dict, name: str = None'''
        super().__init__(config, name=name)
        try:
            with open(self.config.ff_config, 'r') as stream:
                self.config['ff_config'] = yaml.safe_load(stream)
                self.plugins_dir = f'{self.config.ff_config.path_data}/plugins'
            self.plugins_indtalled = self.get_installed_plugins()
        except FileNotFoundError as fnfe:
            self.logger.error(self.journal(str(fnfe)))
            self.plugins_indtalled = {}

    def get_installed_plugins(self):
        '''None -> dict[str, dict]'''
        plugins_indtalled = {}
        for dir in os.listdir(self.plugins_dir):
            try:
                info_file = f'{self.plugins_dir}/{dir}/info.yaml'
                with open(info_file, "r") as stream:
                    try:
                        plugins_indtalled[dir] = yaml.safe_load(stream)
                    except yaml.YAMLError as ye:
                        self.logger.error(self.journal(str(ye)))
            except FileNotFoundError as fnfe:
                self.logger.error(self.journal(f'{fnfe}: {info_file}'))
                continue
        return plugins_indtalled

    def check_command(self, *args):
        '''args: tuple[str] -> bool'''
        return True if self.sub_run(*args).returncode == 0 else False

    def sub_run(self, *args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, encoding="utf-8", **kwargs):
        '''args: args: tuple[str], stdout: int = -1, stderr: int = -2, encoding: str = "utf-8", kwargs: dict[str, Any] -> CompletedProcess'''
        if not self.config.init.execute_commands:
            msg = f'설정값에 의해 명령어를 실행할 수 없음 {args} (execute_commands: {self.config.init.execute_commands})'
            self.logger.error(msg)
            return subprocess.CompletedProcess(args, returncode=1, stderr='', stdout=msg)
        else:
            try:
                # shell=True는 의도치 않은 명령이 실행될 수 있으니 사용하지 않는 쪽으로...
                # command: apt-get install -y, args: "; rm -rf /"이 있을 경우
                # - shell=True : apt-get install -y ; rm -rf /
                # - shell=False: apt-get install -y "; rm -rf /"
                if kwargs.get('shell'):
                    kwargs['shell'] = False
                return subprocess.run(args, stdout=stdout, stderr=stderr, encoding=encoding, **kwargs)
            except Exception as e:
                self.logger.error(self.journal(f'{e}'))
                return subprocess.CompletedProcess(args, returncode=1, stderr='', stdout=str(e))

    def operation_init(self):
        pass


class UbuntuAgent(InitAgent):

    def __init__(self, config):
        '''config: dict'''
        super().__init__(config, name='agent.init.ubuntu')
        self.operations.update(
            {
                'default': self.operation_init,
            }
        )

    def check_process(self, name, timeout):
        '''name: str, timeout: int -> bool'''
        '''ps 명령어가 실행 안 되는 환경이 있음'''
        counter = state = 0
        while state > -1:
            state = self.sub_run('ps', 'aux', timeout=timeout).stdout.find(name)
            if counter > timeout:
                break
            time.sleep(1)
            counter += 1
        return True if state < 0 else False

    def operation_init(self):
        '''None -> None'''
        '''
        test_plugins = [
            'sjva', 'klive_plus', 'wv_tool', 'wavve', 'kakaotv', 'cppl',
            'bot_downloader', 'gds_tool', 'make_yaml', 'flaskfilemanager',
            'terminal', 'ffmpeg', 'number_baseball', 'trans', 'static_host',
            'rclone', 'support_site', 'metadata', 'discord_bot', 'libgdrive',
            'fp_ktv', 'plex_mate', 'vnStat', 'torrent_info', 'tving_search',
            'subtitle_tool', 'fp_movie', 'hotdeal_alarm', 'lotto', 'musicProc2',
            'sporki', 'gugutv', 'narrtv', 'cooltv'
        ]
        '''
        require_plugins = set()
        require_packages = set()
        require_commands = set()

        # plugin by plugin
        for plugin, info in self.plugins_indtalled.items():
           # append this plugin's requires to
            depend_plugins = self.config.init.dependencies.get(plugin, {}).get('plugins', [])
            for depend in depend_plugins:
                require_plugins.add(depend)


            # update dependencies from info.yaml
            '''
            requires = info.get("require_plugin")
            if requires:
                for req in requires:
                    req = req.split("/")[-1]
                    require_plugins.add(req)
            '''

            # append this plugin's packages to
            for depend in self.config.init.dependencies.get(plugin, {}).get('packages', []):
                require_packages.add(depend)

            # append this plugin's commands to
            for depend in self.config.init.dependencies.get(plugin, {}).get('commands', []):
                require_commands.add(depend)

        # pop installed plugins
        for plugin in self.plugins_indtalled.keys():
            require_plugins.discard(plugin)

        executable_commands = []
        # 1. Commands from the config file
        if self.config.init.commands:
            for command in self.config.init.commands:
                executable_commands.append(command)

        # 2. Commands of installing required packages
        if require_packages:
            for req in require_packages:
                command = f'apt-get install -y {req}'
                executable_commands.append(command)

        # 3. Commands from plugin dependencies of the config file
        if require_commands:
            for req in require_commands:
                executable_commands.append(req)

        # 4. Commands of installing required plugins
        if require_plugins:
            for plugin in require_plugins:
                command = f'git clone {self.config.init.dependencies.get(plugin, {"repo": "NO INFO."}).get("repo")} {self.plugins_dir}/{plugin}'
                executable_commands.append(command)

        for command in executable_commands:
            self.logger.info(self.journal(f'실행 예정 명령어: {command}'))

        # run commands
        if self.config.init.execute_commands:
            for command in executable_commands:
                command = shlex.split(command)
                result = self.sub_run(*command, timeout=self.config.init.timeout)
                if result.returncode == 0:
                    msg = '성공'
                else:
                    msg = result.stdout
                self.logger.info(self.journal(f'실행 결과 {command}: {msg}'))
        else:
            self.logger.error(self.journal(f'실행이 허용되지 않도록 설정되어 있어요.'))


'''
Methods
'''


def op_default(config):
    '''args: dict[str, Any] -> None'''
    if config['log']['logger']:
        config['log']['logger'].error(config['args'].parser.print_help())
    else:
        config['args'].parser.print_help()


def op_plexmate(config):
    '''args: dict[str, Any] -> None'''
    plexmate = PlexmateAgent(config)
    plexmate.run()


def op_rclone(config):
    '''args: dict[str, Any] -> None'''
    rclone = RcloneAgent(config)
    rclone.run()


def op_init(config):
    '''args: dict[str, Any] -> None'''
    init_agent = UbuntuAgent(config)
    init_agent.run()


def op_coding(config):
    '''args: dict[str, Any] -> None'''
    if config['args'].agent == 'encode':
        print(str(base64.b64encode(bytes(config['args'].text, 'utf-8')), 'utf-8'))
    elif config['args'].agent == 'decode':
        print(str(base64.b64decode(bytes(config['args'].text, 'utf-8')), 'utf-8'))


def op_test(config):
    '''args: Namespace, config: dict -> None'''
    print('#### test start ####')
    print('#### test end ####')


def parse_args(args):
    '''config: list[Any] -> Namespace'''
    parser = argparse.ArgumentParser(description='Flaskfarm 간단(?) 스크립트')
    parser.set_defaults(func=op_default, parser=parser)
    subparsers = parser.add_subparsers(title='Agents', dest='agent')

    # argument template
    arg_dirs = (
        '--dirs',
        {
            'dest': 'dirs',
            'metavar': '"/path/to/be/refresh"',
            'action': 'extend',
            'nargs': '+',
            'type': str,
            'help': '새로고침할 "로컬" 디렉토리: --dirs "/mnt/gds/A" "/mnt/gds/B"'
        }
    )
    arg_sect = (
        '--sect',
        {
            'dest': 'sections',
            'metavar': '{SECTION ID}',
            'action': 'extend',
            'nargs': '+',
            'type': int,
            'help': '새로고침할 섹션 ID 번호: --sect 1 5 12'
        }
    )
    arg_fs = (
        '--fs',
        {
            'type': str,
            'dest': 'fs',
            'metavar': '{REMOTE:}',
            'help': 'remote: 이름',
        }
    )
    arg_recursive = (
        '--recursive',
        {
            'action': 'store_true',
            'dest': 'recursive',
            'help': 'rclone 플래그에 recursive=true 옵션을 추가 합니다'
        }
    )

    # command: plexmate
    parser_plexmate = subparsers.add_parser(
        'plexmate',
        description='FF에서 LOAD 방식으로 실행해 주세요',
        help='PLEX MATE 관련 명령을 실행합니다'
    )
    parser_plexmate.set_defaults(func=op_plexmate)

    subparsers_plexmate = parser_plexmate.add_subparsers(
        title='Commands',
        dest='command',
        help='아무것도 입력하지 않으면 PLEX MATE의 READY 상태 아이템들을 vfs/refresh 합니다'
    )

    # command: plexmate scan
    parser_plexmate_scan = subparsers_plexmate.add_parser(
        'scan',
        help='PLEX MATE 플러그인에 스캔을 요청합니다'
    )
    parser_plexmate_scan.add_argument(arg_dirs[0], **arg_dirs[1])
    parser_plexmate_scan.add_argument(arg_sect[0], **arg_sect[1])

    # command: plexmate refresh
    parser_plexmate_refresh = subparsers_plexmate.add_parser(
        'refresh',
        help='Rclone 리모트에 vfs/refresh 를 요청한 후 PLEX MATE 에 스캔을 요청합니다'
    )
    parser_plexmate_refresh.add_argument(arg_dirs[0], **arg_dirs[1])
    parser_plexmate_refresh.add_argument(arg_sect[0], **arg_sect[1])
    parser_plexmate_refresh.add_argument(arg_fs[0], **arg_fs[1])
    parser_plexmate_refresh.add_argument(arg_recursive[0], **arg_recursive[1])

    # command: plexmate periodic
    parser_plexmate_periodic = subparsers_plexmate.add_parser(
        'periodic',
        help='주기적 스캔의 작업 ID를 입력하여 vfs/refresh 후 해당 작업을 실행합니다'
    )
    parser_plexmate_periodic.add_argument('job_id', type=int, metavar='{JOB_ID}')
    parser_plexmate_periodic.add_argument(arg_fs[0], **arg_fs[1])
    parser_plexmate_periodic.add_argument(arg_recursive[0], **arg_recursive[1])


    # command: rclone
    parser_rclone = subparsers.add_parser(
        'rclone',
        description='rclone 리모트가 실행중이어야 합니다',
        help='rclone 리모트로 명령을 전송합니다'
    )
    parser_rclone.set_defaults(func=op_rclone)
    subparsers_rclone = parser_rclone.add_subparsers(
        title='Commands',
        dest='command',
        help='vfs/refresh, vfs/list만 구현되어 있습니다.'
    )

    # command: rclone vfs/refresh
    parser_rclone_refresh = subparsers_rclone.add_parser(
        'vfs/refresh',
        description='rclone 리모트가 실행중이어야 합니다',
        help='rclone 리모트에 새로고침 명령을 전송합니다'
    )
    parser_rclone_refresh.add_argument(arg_dirs[0], **arg_dirs[1], required=True)
    parser_rclone_refresh.add_argument(arg_fs[0], **arg_fs[1])
    parser_rclone_refresh.add_argument(arg_recursive[0], **arg_recursive[1])
    parser_rclone_list = subparsers_rclone.add_parser(
        'vfs/list',
        description='rclone 리모트가 실행중이어야 합니다',
        help='rclone 리모트에 vfs/list 명령을 전송합니다'
    )
    parser_rclone_list.add_argument('--fs', type=str, dest='remote', help='remote 이름')

    # command: init
    parser_init = subparsers.add_parser(
        'init',
        description='Flaskfarm 시작시 필요한 명령어를 실행할 때 사용합니다',
        help='Flaskfarm 시작시 실행되는 명령어 모음입니다'
    )
    parser_init.set_defaults(func=op_init)

    # command: encode {string}
    parser_encode = subparsers.add_parser(
        'encode',
        description='Base64 인코딩',
        help='주어진 문자열을 base64로 인코딩 합니다'
    )
    parser_encode.set_defaults(func=op_coding)
    parser_encode.add_argument('text', type=str, help='인코딩하는 문자열')

    # command: decode {encoded string}
    parser_encode = subparsers.add_parser(
        'decode',
        description='Base64 디코딩',
        help='주어진 문자열을 base64로 디코딩 합니다'
    )
    parser_encode.set_defaults(func=op_coding)
    parser_encode.add_argument('text', type=str, help='디코딩하는 문자열')

    # command: test
    parser_test = subparsers.add_parser(
        'test',
        description='테스트 부 명령어',
        help='테스트용'
    )
    parser_test.set_defaults(func=op_test)
    parser_test.add_argument(arg_dirs[0], **arg_dirs[1])

    return parser.parse_args(args)


'''
Execution
'''


def main(*args, **kwargs):
    '''
    Flaskfarm에서 실행하면 호출되는 메소드

    :param *args: 실행 방식과 파일명 ex ['LOAD', '/data/commands/test.py', *args]
    :param **kwargs: 로거가 포함되어 있음 {'logger': <Logger command_x (LOGLEVEL)>}
    '''
    config_file = f'{os.path.dirname(os.path.abspath(__file__))}/ff_aider.yaml'
    config = {}
    with open(config_file, "r") as stream:
        config = yaml.safe_load(stream)
    if not config: raise Exception('설정 정보가 없어요.')
    config.setdefault('log', {'logger': None})['logger'] = kwargs.get('logger')

    def log_it(msg):
        if config['log']['logger']:
            config['log']['logger'].debug(msg)
        else:
            print(msg)

    if args:
        args = list(args)
        args.pop(0)
    else:
        args = list(sys.argv)
    args.pop(0)

    log_it(f'args: {args}')

    try:
        config['args'] = parse_args(args)
        config['args'].func(config)
    except Exception as e:
        log_it(traceback.format_exc())
        log_it(e)

    print('스크립트 완료, 로그를 확인해 주세요.')


if __name__ == "__main__":
    main()
