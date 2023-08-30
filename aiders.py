import os
from pathlib import Path
from datetime import datetime
from typing import Any
import traceback
import shutil
import yaml
import sqlite3
import functools
import subprocess
from subprocess import CompletedProcess
import shlex
import platform
from collections import defaultdict
import time

import requests
from requests import Response

from .setup import PLUGIN, LOGGER, PluginModuleBase, ModelBase, FrameworkJob, PlexServer
from .constants import FRAMEWORK, TASK_KEYS, SCAN_MODE_KEYS, DEPEND_SOURCE_YAML, DEPEND_USER_YAML, SECTION_TYPE_KEYS
from .constants import SETTING_PLEXMATE_MAX_SCAN_TIME, SETTING_PLEXMATE_TIMEOVER_RANGE, SETTING_RCLONE_REMOTE_VFS, SETTING_STARTUP_EXECUTABLE
from .constants import SETTING_RCLONE_REMOTE_ADDR, SETTING_RCLONE_REMOTE_USER, SETTING_RCLONE_REMOTE_PASS, SETTING_RCLONE_MAPPING
from .constants import SETTING_STARTUP_COMMANDS, SETTING_STARTUP_TIMEOUT, SETTING_PLEXMATE_PLEX_MAPPING, SCHEDULE, FF_SCHEDULE_KEYS
from .constants import TOOL_TRASH_KEYS, TOOL_TRASH_TASK_STATUS, STATUS_KEYS


class Aider:

    def __init__(self, name: str = None):
        self.name = name

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

    def get_readable_time(self, _time: float) -> str:
        return datetime.utcfromtimestamp(_time).strftime('%b %d %H:%M')

    def deduplicate(self, items: list[str]) -> list[str]:
        bucket = {}
        for item in items:
            bucket[item] = False
        return list(bucket.keys())

    def parse_mappings(self, text: str) -> dict[str, str]:
        mappings = {}
        if text:
            settings = self.split_by_newline(text)
            for setting in settings:
                source, target = setting.split(':')
                mappings[source.strip()] = target.strip()
        return mappings

    def update_path(self, target: str, mappings: dict) -> str:
        for k, v in mappings.items():
            target = target.replace(k, v)
        return str(Path(target))

    def request(self, method: str = 'POST', url: str = None, data: dict = None, **kwds: Any) -> Response:
        try:
            if method.upper() == 'JSON':
                return requests.request('POST', url, json=data if data else {}, **kwds)
            else:
                return requests.request(method, url, data=data, **kwds)
        except:
            tb = traceback.format_exc()
            LOGGER.error(tb)
            response = requests.Response()
            response._content = bytes(tb, 'utf-8')
            response.status_code = 0
            return response

    def log_response(self, response: Response) -> None:
        try:
            msg = f'code: {response.status_code}, content: {response.json()}'
        except requests.exceptions.JSONDecodeError:
            msg = f'code: {response.status_code}, content: {response.text}'
        LOGGER.info(msg)


class JobAider(Aider):

    def __init__(self):
        super().__init__()

    @FRAMEWORK.celery.task(bind=True)
    def start_job(self, job: ModelBase) -> None:
        # bind=True, self 는 task 의 instance
        if job.task == TASK_KEYS[0]:
            '''refresh_scan'''
            plexmateaider = PlexmateAider()
            rcloneaider = RcloneAider()
            # refresh
            if job.scan_mode == SCAN_MODE_KEYS[1] and job.periodic_id > 0:
                # 주기적 스캔 작업 새로고침
                targets = plexmateaider.get_periodic_locations(job.periodic_id)
                for target in targets:
                    rcloneaider.vfs_refresh(target)
            else:
                rcloneaider.vfs_refresh(job.target)
            # scan
            plexmateaider.scan(job.scan_mode, job.target, job.periodic_id)
        elif job.task == TASK_KEYS[1]:
            '''refresh'''
            rcloneaider = RcloneAider()
            rcloneaider.vfs_refresh(job.target)
            pass
        elif job.task == TASK_KEYS[2]:
            '''scan'''
            plexmateaider = PlexmateAider()
            plexmateaider.scan(job.scan_mode, job.target, job.periodic_id)
        elif job.task == TASK_KEYS[3]:
            '''pm_ready_refresh'''
            # plexmate
            plexmateaider = PlexmateAider()
            plexmateaider.check_scanning(int(PLUGIN.ModelSetting.get(SETTING_PLEXMATE_MAX_SCAN_TIME)))
            plexmateaider.check_timeover(PLUGIN.ModelSetting.get(SETTING_PLEXMATE_TIMEOVER_RANGE))
            # refresh
            targets = plexmateaider.get_scan_targets('READY')
            if targets:
                rcloneaider = RcloneAider()
                for target in targets:
                    response = rcloneaider.vfs_refresh(target)
                    result, reason = rcloneaider.is_successful(response)
                    if not result:
                        LOGGER.warning(f'새로고침 실패: [{target}]: {reason}')
            else:
                LOGGER.info(f'새로고침 대상이 없습니다.')
        elif job.task == TASK_KEYS[4]:
            '''clear'''
            plexmateaider = PlexmateAider()
            plexmateaider.clear_section(job.clear_section, job.clear_type, job.clear_level)
        elif job.task == TASK_KEYS[5]:
            '''startup'''
            ubuntuaider = UbuntuAider()
            ubuntuaider.startup()
            pass
        elif job.task == TASK_KEYS[6]:
            '''trash'''
            pass
        elif job.task in TOOL_TRASH_KEYS:
            '''trash_refresh_scan'''
            PLUGIN.ModelSetting.set(TOOL_TRASH_TASK_STATUS, STATUS_KEYS[1])
            try:
                plexmateaider = PlexmateAider()
                if job.task == TOOL_TRASH_KEYS[2] and \
                PLUGIN.ModelSetting.get(TOOL_TRASH_TASK_STATUS) == STATUS_KEYS[1]:
                    plexmateaider.empty_trash(job.section_id)
                else:
                    # get trash items
                    trashes: dict = plexmateaider.get_trashes(job.section_id, 1, -1)
                    paths = {Path(row['file']).parent for row in trashes}
                    rcloneaider = RcloneAider()
                    for path in paths:
                        if PLUGIN.ModelSetting.get(TOOL_TRASH_TASK_STATUS) != STATUS_KEYS[1]:
                            LOGGER.info(f'작업을 중지합니다.')
                            break
                        if job.task == TOOL_TRASH_KEYS[0] or \
                        job.task == TOOL_TRASH_KEYS[3] or \
                        job.task == TOOL_TRASH_KEYS[4]:
                            rcloneaider.vfs_refresh(path)
                        if job.task == TOOL_TRASH_KEYS[1] or \
                        job.task == TOOL_TRASH_KEYS[3] or \
                        job.task == TOOL_TRASH_KEYS[4]:
                            plexmateaider.scan(SCAN_MODE_KEYS[2], path)
                    if job.task == TOOL_TRASH_KEYS[4] and \
                    PLUGIN.ModelSetting.get(TOOL_TRASH_TASK_STATUS) == STATUS_KEYS[1]:
                        plexmateaider.empty_trash(job.section_id)
            except:
                LOGGER.error(traceback.format_exc())
            finally:
                PLUGIN.ModelSetting.set(TOOL_TRASH_TASK_STATUS, STATUS_KEYS[0])

    @classmethod
    def create_schedule_id(cls, job_id: int, middle: str = SCHEDULE) -> str:
        return f'{PLUGIN.package_name}_{middle}_{job_id}'

    @classmethod
    def add_schedule(cls, id: int, job: ModelBase = None) -> bool:
        try:
            from .models import Job
            job = job if job else Job.get_by_id(id)
            schedule_id = cls.create_schedule_id(job.id)
            if not FRAMEWORK.scheduler.is_include(schedule_id):
                sch = FrameworkJob(__package__, schedule_id, job.schedule_interval, cls.start_job, job.desc, args=(job,))
                FRAMEWORK.scheduler.add_job_instance(sch)
            return True
        except Exception as e:
            LOGGER.error(traceback.format_exc())
            return False

    @classmethod
    def set_schedule(cls, job_id: int | str, active: bool = False) -> tuple[bool, str]:
        from .models import Job
        schedule_id = cls.create_schedule_id(job_id)
        is_include = FRAMEWORK.scheduler.is_include(schedule_id)
        job = Job.get_by_id(job_id)
        schedule_mode = job.schedule_mode if job else FF_SCHEDULE_KEYS[0]
        if schedule_mode == FF_SCHEDULE_KEYS[2]:
            if active and is_include:
                result, data = False, f'이미 일정에 등록되어 있습니다.'
            elif active and not is_include:
                result = cls.add_schedule(job_id)
                data = '일정에 등록했습니다.' if result else '일정에 등록하지 못했어요.'
            elif not active and is_include:
                result, data = FRAMEWORK.scheduler.remove_job(schedule_id), '일정에서 제외했습니다.'
            else:
                result, data = False, '등록되지 않은 일정입니다.'
        else:
            result, data = False, f'등록할 수 없는 일정 방식입니다.'
        return result, data


class SettingAider(Aider):

    def __init__(self):
        super().__init__()

    def remote_command(self, command: str, url: str, username: str, password: str) -> requests.Response:
        LOGGER.debug(url)
        return self.reqest('POST', f'{url}/{command}', auth=(username, password))

    def depends(self, text: str = None):
        try:
            if not DEPEND_USER_YAML.exists():
                shutil.copyfile(DEPEND_SOURCE_YAML, DEPEND_USER_YAML)
            if text:
                with DEPEND_USER_YAML.open(mode='w') as file:
                    file.write(text)
                    depends = text
            else:
                with DEPEND_USER_YAML.open() as file:
                    depends = file.read()
            return depends
        except Exception as e:
            LOGGER.error(traceback.format_exc())
            if text: return text
            else:
                with DEPEND_SOURCE_YAML.open() as file:
                    return file.read()


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

    def format_file_size(self, size: int, decimals: int = 1, binary_system: bool = True) -> str:
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


class PluginAider(Aider):

    def __init__(self, name: str):
        super().__init__(name)

    @property
    def plugin(self):
        plugin = FRAMEWORK.PluginManager.get_plugin_instance(self.name)
        if plugin:
            return plugin
        else:
            raise Exception(f'플러그인을 찾을 수 없습니다: {self.name}')

    def dict_factory(cursor: sqlite3.Cursor, row: tuple) -> dict:
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    def check_plugin(func: callable) -> callable:
        @functools.wraps(func)
        def wrap(*args, **kwds):
            if args[0].plugin:
                return func(*args, **kwds)
            else:
                raise Exception(f'플러그인을 찾을 수 없습니다: {args[0].name}')
        return wrap

    @check_plugin
    def get_module(self, module: str) -> PluginModuleBase:
        return self.plugin.logic.get_module(module)


class PlexmateAider(PluginAider):

    _plex_server = None

    def __init__(self):
        super().__init__('plex_mate')
        self.db = self.plugin.PlexDBHandle

    @property
    def plex_server(self):
        if not self._plex_server:
            self._plex_server = PlexServer(self.plugin.ModelSetting.get('base_url'), self.plugin.ModelSetting.get('base_token'))
        return self._plex_server

    def get_scan_model(self) -> ModelBase:
        return self.get_module('scan').web_list_model

    def get_scan_items(self, status: str) -> list[ModelBase]:
        return self.get_scan_model().get_list_by_status(status)

    def get_scan_targets(self, status: str) -> list[str]:
        targets = [scan_item.target for scan_item in self.get_scan_items(status)]
        return self.deduplicate(targets)

    def get_sections(self) -> dict[str, Any]:
        sections = defaultdict(list)
        sections[SECTION_TYPE_KEYS[0]] = [{'id': item['id'], 'name': item['name']} for item in self.db.library_sections(section_type=1)]
        sections[SECTION_TYPE_KEYS[1]] = [{'id': item['id'], 'name': item['name']} for item in self.db.library_sections(section_type=2)]
        sections[SECTION_TYPE_KEYS[2]] = [{'id': item['id'], 'name': item['name']} for item in self.db.library_sections(section_type=8)]
        return sections

    def get_periodics(self) -> list[dict[str, Any]]:
        periodics = []
        jobs = self.get_module('periodic').get_jobs()
        for job in jobs:
            idx = int(job['job_id'].replace('plex_mate_periodic_', '')) + 1
            section = job.get('섹션ID', -1)
            section_data = self.db.library_section(section)
            if section_data:
                name = section_data.get('name')
            else:
                LOGGER.debug(f'존재하지 않는 섹션: {section}')
                continue
            periodics.append({'idx': idx, 'name': name, 'desc': job.get('설명', '')})
        return periodics

    def get_trashes(self, section_id: int, page_no: int = 1, limit: int = 10) -> dict[str, Any]:
        query = '''
        SELECT media_items.id, media_items.metadata_item_id, media_items.deleted_at, media_parts.file
        FROM media_parts, media_items
        WHERE media_items.deleted_at != ''
            AND media_items.library_section_id = {section_id}
            AND media_items.id = media_parts.media_item_id
        ORDER BY media_parts.file
        LIMIT {limit} OFFSET {offset}
        '''
        offset = (page_no - 1) * limit
        with sqlite3.connect(self.plugin.ModelSetting.get('base_path_db')) as con:
            con.row_factory = PluginAider.dict_factory
            cs = con.cursor()
            return cs.execute(query.format(section_id=section_id, limit=limit, offset=offset)).fetchall()

    def get_trash_list(self, section_id: int, page_no: int = 1, limit: int = 10) -> dict[str, Any]:
        '''
        plex_server = PlexServer(self.plugin.ModelSetting.get('base_url'), self.plugin.ModelSetting.get('base_token'))
        movie:
            videos: plexapi.video.Movie = plex_server.library.sectionByID(section_id).search(filters={"trash": True})
        episode:
            libtype:
                movie, show, season, episode, artist, album, track, photoalbum
                Default is the main library type.
            videos: plexapi.video.Episode = plex_server.library.sectionByID(section_id).search(libtype='episode', filters={"trash": True})
        exists:
            for v in videos:
                v.reload() # It takes a long time.
                v.media[0].parts[0].exists
                v.media[0].parts[0].accessible
        '''
        result = {'total': 0, 'limit': limit, 'page': page_no, 'section_id': section_id, 'total_paths': 0, 'data': None}
        total_rows = self.get_trashes(section_id, 1, -1)
        paths ={Path(row['file']).parent for row in total_rows}
        result['total'] = len(total_rows)
        result['total_paths'] = len(paths)
        rows = self.get_trashes(section_id, page_no, limit)
        if len(rows) > 0:
            for row in rows:
                row['deleted_at'] = self.get_readable_time(row['deleted_at'])
            result['data'] = rows
        return result

    def check_scanning(self, max_scan_time: int) -> None:
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
                    LOGGER.warning(f'스캔 시간 {max_scan_time}분 초과: {scan.target}')
                    LOGGER.warning(f'스캔 QUEUE에서 제외: {scan.target}')
                    model.delete_by_id(scan.id)
                    new_item = model(scan.target)
                    new_item.id = scan.id
                    new_item.save()

    def check_timeover(self, item_range: str) -> None:
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
                    LOGGER.warning(f'READY 로 상태 변경: {over.id} {over.target}')
                    over.set_status('READY', save=True)

    def scan(self, scan_mode: str, target: str = None, periodic_id: int = -1) -> None:
        if scan_mode == SCAN_MODE_KEYS[2]:
            mappings = self.parse_mappings(PLUGIN.ModelSetting.get(SETTING_PLEXMATE_PLEX_MAPPING))
            target = self.update_path(target, mappings)
            rows = self.db.select('SELECT library_section_id, root_path FROM section_locations')
            founds = set()
            for row in rows:
                root = row['root_path']
                longer = target if len(target) >= len(root) else root
                shorter = target if len(target) < len(root) else root
                if longer.startswith(shorter):
                    founds.add(int(row['library_section_id']))
            if founds:
                LOGGER.debug(f'섹션 ID: {founds}')
                for section_id in founds:
                    section = self.plex_server.library.sectionByID(section_id)
                    max_seconds = 300
                    start = time.time()
                    section.update(path=target)
                    section.reload()
                    LOGGER.debug(f'스캔 중: {target}')
                    '''
                    스캔 추적을 섹션 상태에 의존
                    다른 곳에서 동일 섹션을 스캔 시도할 경우?
                    '''
                    while section.refreshing:
                        if (time.time() - start) >= max_seconds:
                            break
                        time.sleep(1)
                        section.reload()
                    if time.time() - start > max_seconds:
                        LOGGER.warning(f'스캔 대기 시간 초과: {target} ... {(time.time() - start):.1f}s')
                    else:
                        LOGGER.info(f'스캔 완료: {target} ... {(time.time() - start):.1f}s')
            else:
                LOGGER.error(f'섹션 ID를 찾을 수 없습니다: {target}')
        elif scan_mode == SCAN_MODE_KEYS[1]:
            module = self.get_module('periodic')
            scan_job = self.get_periodic_job(periodic_id)
            if scan_job:
                LOGGER.debug(f'주기적 스캔 작업 실행: {scan_job}')
                module.one_execute(periodic_id - 1)
        else:
            scan_item = self.get_scan_model()(target)
            scan_item.save()
            LOGGER.info(f'plex_mate 스캔 ID: {scan_item.id}')

    def get_locations_by_id(self, section_id: int) -> list[str]:
        return [location.get('root_path') for location in self.db.section_location(library_id=section_id)]

    def get_section_by_id(self, section_id: int) -> dict[str, Any]:
        return self.db.library_section(section_id)

    def get_periodic_locations(self, periodic_id: int) -> list[str]:
        job = self.get_periodic_job(periodic_id)
        try:
            if job.get('폴더'):
                targets = list(job.get('폴더'))
            else:
                targets = self.get_locations_by_id(job.get('섹션ID'))
        except:
            LOGGER.error(traceback.format_exc())
            targets = []
        finally:
            return targets

    def get_periodic_job(self, periodic_id: int) -> dict:
        mod = self.get_module('periodic')
        periodic_id -= 1
        try:
            job = mod.get_jobs()[periodic_id]
        except IndexError:
            LOGGER.error(f'주기적 스캔 작업을 찾을 수 없습니다: {periodic_id + 1}')
            job = {}
        finally:
            return job

    def clear_section(self, section_id: int, clear_type: str, clear_level: str) -> None:
        mod = self.get_module('clear')
        page = mod.get_page(clear_type)
        info = f'{clear_level}, {self.get_section_by_id(section_id).get("name")}'
        LOGGER.info(f'파일 정리 시작: {info}')
        page.task_interface(clear_level, section_id, 'false').join()
        LOGGER.info(f'파일 정리 종료: {info}')

    def delete_media(self, meta_id: int, media_id: int) -> str:
        """
        #/library/metadata/508092/media/562600
        plex_url = self.plugin.ModelSetting.get('base_url')
        plex_token = self.plugin.ModelSetting.get('base_token')
        url = f'{plex_url}/library/metadata/{meta_id}/media/{media_id}'
        params = {
            'X-Plex-Token': plex_token
        }
        response = self.request('DELETE', url, params=params)
        """
        try:
            video = self.plex_server.library.fetchItem(meta_id, Media__id=media_id).reload()
            for media in video.media:
                if media.id == media_id:
                    non_exists = []
                    for part in media.parts:
                        if not part.exists:
                            non_exists.append(part.file)
                    if non_exists:
                        LOGGER.debug(f'삭제: {non_exists}')
                        media.delete()
            return '삭제했습니다.'
        except:
            LOGGER.error(traceback.format_exc())
            return '오류가 발생했습니다.'

    def empty_trash(self, section_id: int) -> None:
        LOGGER.debug(f'휴지통을 비우는 중입니다: {section_id}')
        self.plex_server.library.sectionByID(section_id).emptyTrash()


class RcloneAider(Aider):

    def __init__(self):
        super().__init__()

    def get_metadata_cache(self, fs: str) -> tuple[int, int]:
        result = self.vfs_stats(fs).json().get("metadataCache")
        return result.get('dirs', 0), result.get('files', 0)

    def vfs_stats(self, fs: str) -> Response:
        return self.command("vfs/stats", data={"fs": fs})

    def command(self, command: str, data: dict = None) -> Response:
        return self.request(
            "JSON",
            f'{PLUGIN.ModelSetting.get(SETTING_RCLONE_REMOTE_ADDR)}/{command}',
            data=data,
            auth=(PLUGIN.ModelSetting.get(SETTING_RCLONE_REMOTE_USER), PLUGIN.ModelSetting.get(SETTING_RCLONE_REMOTE_PASS))
        )

    def _vfs_refresh(self, remote_path: str, recursive: bool = False, fs: str = None) -> Response:
        data = {
            'recursive': str(recursive).lower(),
            'fs': fs if fs else PLUGIN.ModelSetting.get(SETTING_RCLONE_REMOTE_VFS),
            'dir': remote_path
        }
        start_dirs, start_files = self.get_metadata_cache(data["fs"])
        start = time.time()
        response = self.command('vfs/refresh', data=data)
        dirs, files = self.get_metadata_cache(data["fs"])
        self.log_response(response)
        LOGGER.debug(f'vfs/refresh: dirs={dirs - start_dirs} files={files - start_files} elapsed={(time.time() - start):.1f}s')
        return response

    def vfs_refresh(self, local_path: str) -> Response:
        # 이미 존재하는 파일이면 패스, 존재하지 않은 파일/폴더, 존재하는 폴더이면 진행
        local_path = Path(local_path)
        if local_path.is_file():
            response = requests.Response()
            response.status_code = 0
            reason = '이미 존재하는 파일입니다.'
            response._content = bytes(reason, 'utf-8')
            LOGGER.debug(f'{reason}: {local_path}')
        else:
            # vfs/refresh 용 존재하는 경로 찾기
            test_dirs = [local_path]
            already_exists = test_dirs[0].exists()
            while not test_dirs[-1].exists():
                test_dirs.append(test_dirs[-1].parent)
            LOGGER.debug(f"경로 검사: {str(test_dirs)}")
            mappings = self.parse_mappings(PLUGIN.ModelSetting.get(SETTING_RCLONE_MAPPING))
            while test_dirs:
                # vfs/refresh 후
                response = self._vfs_refresh(self.update_path(str(test_dirs[-1]), mappings))
                # 타겟이 존재하는지 점검
                if local_path.exists():
                    # 존재하지 않았던 폴더면 vfs/refresh
                    if not local_path.is_file() and not already_exists:
                        self._vfs_refresh(self.update_path(str(local_path), mappings))
                        # 새로운 폴더를 새로고침 후 한번 더 타겟 경로 존재 점검
                        if not local_path.exists() and len(test_dirs) > 1: continue
                    break
                else:
                    result, reason = self.is_successful(response)
                    if not result:
                        LOGGER.error(f'새로고침 실패: {reason}: {test_dirs[-1]}')
                        break
                # 타겟이 아직 존재하지 않으면 다음 상위 경로로 시도
                test_dirs.pop()
        return response

    def is_successful(self, response: Response) -> tuple[bool, str]:
        if not str(response.status_code).startswith('2'):
            return False, f'status code: {response.status_code}, content: {response.text}'
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
        except:
            LOGGER.error(traceback.format_exc())
            return False, response.text


class StatupAider(Aider):

    def __init__(self):
        super().__init__()

    def sub_run(self, *args: tuple[str],
                stdout: int = subprocess.PIPE, stderr: int = subprocess.STDOUT,
                encoding: str = 'utf-8', **kwds: dict[str, Any]) -> CompletedProcess:
        startup_executable = PLUGIN.ModelSetting.get(SETTING_STARTUP_EXECUTABLE)
        startup_executable = True if startup_executable.lower() == 'true' else False
        if not startup_executable:
            msg = f'실행이 허용되지 않았어요.'
            LOGGER.error(msg)
            return subprocess.CompletedProcess(args, returncode=1, stderr='', stdout=msg)
        else:
            try:
                # shell=True는 의도치 않은 명령이 실행될 수 있으니 항상 False로...
                if kwds.get('shell'):
                    kwds['shell'] = False
                return subprocess.run(args, stdout=stdout, stderr=stderr, encoding=encoding, **kwds)
            except Exception as e:
                LOGGER.error(traceback.format_exc())
                return subprocess.CompletedProcess(args, returncode=1, stderr='', stdout=str(e))

    def startup(self) -> None:
        pass


class UbuntuAider(StatupAider):

    def __init__(self):
        super().__init__()

    def startup(self) -> None:
        if platform.system().lower() != 'linux':
            LOGGER.warning(f'실행할 수 없는 OS 환경입니다: {platform.system()}')
            return

        require_plugins = set()
        require_packages = set()
        require_commands = set()

        plugins_installed = [plugin_name for plugin_name in FRAMEWORK.PluginManager.all_package_list.keys()]
        depends = yaml.safe_load(SettingAider().depends()).get('dependencies')

        # plugin by plugin
        for plugin in plugins_installed:
           # append this plugin's requires to
            depend_plugins = depends.get(plugin, {}).get('plugins', [])
            for depend in depend_plugins:
                if depend not in plugins_installed:
                    require_plugins.add(depend)

            # append this plugin's packages to
            for depend in depends.get(plugin, {}).get('packages', []):
                require_packages.add(depend)

            # append this plugin's commands to
            for depend in depends.get(plugin, {}).get('commands', []):
                require_commands.add(depend)

        executable_commands = []
        # 1. Commands from the config file
        setiing_commands = self.split_by_newline(PLUGIN.ModelSetting.get(SETTING_STARTUP_COMMANDS))
        if setiing_commands:
            for command in setiing_commands:
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
                LOGGER.info(f'설치 예정 플러그인: {plugin}')

        for command in executable_commands:
            LOGGER.info(f'실행 예정 명령어: {command}')

        # run commands
        startup_executable = PLUGIN.ModelSetting.get(SETTING_STARTUP_EXECUTABLE)
        startup_executable = True if startup_executable.lower() == 'true' else False
        if startup_executable:
            for command in executable_commands:
                command = shlex.split(command)
                result: CompletedProcess = self.sub_run(*command, timeout=int(PLUGIN.ModelSetting.get(SETTING_STARTUP_TIMEOUT)))
                if result.returncode == 0:
                    msg = '성공'
                else:
                    msg = result.stdout
                LOGGER.info(f'실행 결과 {command}: {msg}')

            for plugin in require_plugins:
                result = FRAMEWORK.PluginManager.plugin_install(depends.get(plugin, {"repo": "NO INFO."}).get("repo"))
                LOGGER.info(result.get('msg'))
        else:
            LOGGER.warning(f'실행이 허용되지 않았어요.')