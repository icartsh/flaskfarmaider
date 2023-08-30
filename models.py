from datetime import datetime
import traceback
from typing import Any

from .aiders import JobAider
from .setup import PLUGIN, LOGGER, LocalProxy, Query, desc, ModelBase
from .constants import FRAMEWORK, FF_SCHEDULE_KEYS, SCAN_MODE_KEYS, STATUS_KEYS, SCHEDULE, TASK_KEYS, TASKS


class Job(ModelBase):

    P = PLUGIN
    __tablename__ = f'{PLUGIN.package_name}_jobs'
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
    scan_mode = FRAMEWORK.db.Column(FRAMEWORK.db.String)
    periodic_id = FRAMEWORK.db.Column(FRAMEWORK.db.Integer)
    clear_type = FRAMEWORK.db.Column(FRAMEWORK.db.String)
    clear_section = FRAMEWORK.db.Column(FRAMEWORK.db.Integer)
    clear_level = FRAMEWORK.db.Column(FRAMEWORK.db.String)

    def __init__(self, task: str = '', schedule_mode: str = FF_SCHEDULE_KEYS[0], schedule_auto_start: bool = False,
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

    def update(self, info: dict) -> ModelBase:
        self.task = info.get('task', self.task)
        self.schedule_mode = info.get('schedule_mode', self.schedule_mode)
        self.schedule_auto_start = info.get('schedule_auto_start', self.schedule_auto_start)
        self.desc = info.get('desc', self.desc)
        self.target = info.get('target', self.target)
        self.recursive = info.get('recursive', self.recursive)
        self.vfs = info.get('vfs', self.vfs)
        self.scan_mode = info.get('scan_mode', self.scan_mode)
        self.periodic_id = info.get('periodic_id', self.periodic_id)
        self.clear_type = info.get('clear_type', self.clear_type)
        self.clear_level = info.get('clear_level', self.clear_level)
        self.clear_section = info.get('clear_section', self.clear_section)
        return self

    @classmethod
    def update_formdata(cls, formdata: dict[str, list]) -> ModelBase:
        _id = int(formdata.get('id')[0]) if formdata.get('id') else -1
        if _id == -1:
            model = Job()
        else:
            model = cls.get_by_id(_id)
        try:
            model.task = formdata.get('sch-task')[0] if formdata.get('sch-task') else TASK_KEYS[0]
            desc = formdata.get('sch-description')[0] if formdata.get('sch-description') else ''
            model.desc = desc if desc != '' else f'{TASKS[model.task]["name"]}'
            model.schedule_mode = formdata.get('sch-schedule-mode')[0] if formdata.get('sch-schedule-mode') else FF_SCHEDULE_KEYS[0]
            model.schedule_interval = formdata.get('sch-schedule-interval')[0] if formdata.get('sch-schedule-interval') else '60'
            if model.task == TASK_KEYS[5]:
                model.target = ''
                model.schedule_interval = '매 시작'
            elif model.task == TASK_KEYS[3]:
                model.target = ''
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

            schedule_id = JobAider.create_schedule_id(model.id)
            is_include = FRAMEWORK.scheduler.is_include(schedule_id)
            if is_include:
                FRAMEWORK.scheduler.remove_job(schedule_id)
                if model.schedule_mode == FF_SCHEDULE_KEYS[2]:
                    LOGGER.debug(f'일정에 재등록합니다: {schedule_id}')
                    JobAider.add_schedule(model.id)
            model.save()
        except:
            LOGGER.error(traceback.format_exc())
            LOGGER.error('작업을 저장하지 못했습니다.')
        finally:
            return model

    @classmethod
    def get_job(cls, id: int = -1, info: dict = None) -> ModelBase:
        if id > 0:
            job = cls.get_by_id(id)
        elif info:
            job = Job().update(info)
        else:
            job = Job()
        return job

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
                item['is_include'] = True if FRAMEWORK.scheduler.is_include(JobAider.create_schedule_id(item['id'])) else False
                item['is_running'] = True if FRAMEWORK.scheduler.is_running(JobAider.create_schedule_id(item['id'])) else False
                ret['list'].append(item)
            ret['paging'] = cls.get_paging_info(count, page, page_size)
            PLUGIN.ModelSetting.set(f'{SCHEDULE}_last_list_option', f'{order}|{page}|{search}|{option1}|{option2}')
            return ret
        except:
            LOGGER.error(traceback.format_exc())
