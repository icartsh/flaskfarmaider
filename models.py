from datetime import datetime
import traceback
from typing import Any

from werkzeug.local import LocalProxy # type: ignore
from flask_sqlalchemy.query import Query # type: ignore
from sqlalchemy import desc # type: ignore

from plugin.model_base import ModelBase # type: ignore

from .setup import PLUGIN, FRAMEWORK, SCHEDULE, LOGGER


TASK_KEYS = ('refresh_scan', 'refresh', 'scan', 'pm_ready_refresh', 'clear', 'startup')
TASKS = {
    TASK_KEYS[0]: {'key': TASK_KEYS[0], 'name': '새로고침 후 스캔', 'desc': 'Rclone 리모트 콘트롤 서버에 vfs/refresh 요청 후 플렉스 스캔', 'enable': False},
    TASK_KEYS[1]: {'key': TASK_KEYS[1], 'name': '새로고침', 'desc': 'Rclone 리모트 콘트롤 서버에 vfs/refresh 요청', 'enable': False},
    TASK_KEYS[2]: {'key': TASK_KEYS[2], 'name': '스캔', 'desc': '플렉스 스캔을 요청', 'enable': False},
    TASK_KEYS[3]: {'key': TASK_KEYS[3], 'name': 'Plexmate Ready 새로고침', 'desc': 'Plexmate의 READY 상태인 항목들을 Rclone 리모트 서버에 vfs/refresh 요청', 'enable': False},
    TASK_KEYS[4]: {'key': TASK_KEYS[4], 'name': 'Plexmate 파일 정리', 'desc': 'Plexmate의 라이브러리 파일 정리를 일정으로 등록', 'enable': False},
    TASK_KEYS[5]: {'key': TASK_KEYS[5], 'name': '시작 스크립트', 'desc': 'Flaskfarm 시작시 필요한 OS 명령어를 실행', 'enable': False},
}

STATUS_KEYS = ('ready', 'running', 'finish')
STATUSES = {
    STATUS_KEYS[0]: {'key': STATUS_KEYS[0], 'name': '대기중', 'desc': None},
    STATUS_KEYS[1]: {'key': STATUS_KEYS[1], 'name': '실행중', 'desc': None},
    STATUS_KEYS[2]: {'key': STATUS_KEYS[2], 'name': '완료', 'desc': None},
}

FF_SCHEDULE_KEYS = ('none', 'startup', 'schedule')
FF_SCHEDULES = {
    FF_SCHEDULE_KEYS[0]: {'key': FF_SCHEDULE_KEYS[0], 'name': '없음', 'desc': None},
    FF_SCHEDULE_KEYS[1]: {'key': FF_SCHEDULE_KEYS[1], 'name': '시작시 실행', 'desc': None},
    FF_SCHEDULE_KEYS[2]: {'key': FF_SCHEDULE_KEYS[2], 'name': '시간 간격', 'desc': None},
}

SCAN_MODE_KEYS = ('plexmate', 'periodic', 'web')
SCAN_MODES = {
    SCAN_MODE_KEYS[0]: {'key': SCAN_MODE_KEYS[0], 'name': 'Plexmate 스캔', 'desc': None},
    SCAN_MODE_KEYS[1]: {'key': SCAN_MODE_KEYS[1], 'name': '주기적 스캔', 'desc': None},
    SCAN_MODE_KEYS[2]: {'key': SCAN_MODE_KEYS[2], 'name': 'Plex Web API', 'desc': None},
}


class Job(ModelBase):

    P = PLUGIN
    __tablename__ = f'{__package__}_jobs'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = PLUGIN.package_name

    id = FRAMEWORK.db.Column(FRAMEWORK.db.Integer, primary_key=True)
    ctime = FRAMEWORK.db.Column(FRAMEWORK.db.DateTime)
    ftime = FRAMEWORK.db.Column(FRAMEWORK.db.DateTime)
    desc = FRAMEWORK.db.Column(FRAMEWORK.db.String)
    target = FRAMEWORK.db.Column(FRAMEWORK.db.String)
    task = FRAMEWORK.db.Column(FRAMEWORK.db.String)
    recursive = FRAMEWORK.db.Column(FRAMEWORK.db.Boolean)
    vfs = FRAMEWORK.db.Column(FRAMEWORK.db.String)
    schedule_mode = FRAMEWORK.db.Column(FRAMEWORK.db.String)
    schedule_interval = FRAMEWORK.db.Column(FRAMEWORK.db.String)
    schedule_auto_start = FRAMEWORK.db.Column(FRAMEWORK.db.Boolean)
    status = FRAMEWORK.db.Column(FRAMEWORK.db.String)
    journal = FRAMEWORK.db.Column(FRAMEWORK.db.Text)
    scan_mode = FRAMEWORK.db.Column(FRAMEWORK.db.String)
    periodic_id = FRAMEWORK.db.Column(FRAMEWORK.db.Integer)
    clear_type = FRAMEWORK.db.Column(FRAMEWORK.db.String)
    clear_section = FRAMEWORK.db.Column(FRAMEWORK.db.Integer)
    clear_level = FRAMEWORK.db.Column(FRAMEWORK.db.String)

    def __init__(self, task: str, schedule_mode: str = FF_SCHEDULE_KEYS[0], schedule_auto_start: bool = False,
                 desc: str = '', target: str = '', recursive: bool = False,
                 vfs: str = '', scan_mode: str = SCAN_MODE_KEYS[0], periodic_id: int = -1,
                 clear_type: str = '', clear_level: str = '', clear_section: int = -1):
        self.ctime = datetime.now()
        self.ftime = datetime(1970, 1, 1)
        self.task = task
        self.schedule_mode = schedule_mode
        self.schedule_auto_start = schedule_auto_start
        self.desc = desc
        self.target = target
        self.recursive = recursive
        self.vfs = vfs
        self.status = STATUS_KEYS[0]
        self.scan_mode = scan_mode
        self.periodic_id = periodic_id
        self.clear_type = clear_type
        self.clear_level = clear_level
        self.clear_section = clear_section

    @classmethod
    def make_query(cls, request: LocalProxy, order: str ='desc', search: str = '', option1: str = 'all', option2: str = 'all') -> Query:
        '''override'''
        with FRAMEWORK.app.app_context():
            query = cls.make_query_search(FRAMEWORK.db.session.query(cls), search, cls.target)
            if option1 != 'all':
                query = query.filter(cls.task == option1)
            if option2 != 'all':
                query = query.filter(cls.status == option2)
            if order == 'desc':
                query = query.order_by(desc(cls.id))
            else:
                query = query.order_by(cls.id)
            return query

    def set_status(self, status: str, save: bool = True) -> 'Job':
        if status in STATUS_KEYS:
            self.status = status
            if status == STATUS_KEYS[2]:
                self.ftime = datetime.now()
            if save:
                self.save()
        else:
            LOGGER.error(f'wrong status: {status}')
        return self

    @classmethod
    def web_list(cls, req: LocalProxy) -> dict[str, Any] | None:
        '''override'''
        try:
            ret = {}
            page = 1
            page_size = 30
            search = ''
            if 'page' in req.form:
                page = int(req.form['page'])
            if 'keyword' in req.form:
                search = req.form['keyword'].strip()
            option1 = req.form.get('option1', 'all')
            option2 = req.form.get('option2', 'all')
            order = req.form['order'] if 'order' in req.form else 'desc'
            query = cls.make_query(req, order=order, search=search, option1=option1, option2=option2)
            count = query.count()
            query = query.limit(page_size).offset((page-1)*page_size)
            lists = query.all()
            ret['list'] = []
            for item in lists:
                item = item.as_dict()
                item['is_include'] = True if FRAMEWORK.scheduler.is_include(cls.create_schedule_id(item['id'])) else False
                item['is_running'] = True if FRAMEWORK.scheduler.is_running(cls.create_schedule_id(item['id'])) else False
                ret['list'].append(item)
            ret['paging'] = cls.get_paging_info(count, page, page_size)
            PLUGIN.ModelSetting.set(f'{SCHEDULE}_last_list_option', f'{order}|{page}|{search}|{option1}|{option2}')
            return ret
        except Exception as e:
            LOGGER.error(f"Exception:{str(e)}")
            LOGGER.error(traceback.format_exc())

    @classmethod
    def create_schedule_id(cls, job_id: int) -> str:
        return f'{__package__}_{job_id}'
