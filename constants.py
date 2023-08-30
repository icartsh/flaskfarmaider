import pathlib

from .setup import Framework

FRAMEWORK = Framework.get_instance()
SETTING = 'setting'
SCHEDULE = 'schedule'
TOOL = 'tool'
TOOL_TRASH = 'trash'
MANUAL = 'manual'
LOG = 'log'
PKG_PATH = pathlib.Path(__file__).parent
README = PKG_PATH / 'README.md'
DEPEND_SOURCE_YAML = PKG_PATH / 'files' / 'flaskfarmaider.yaml'
DEPEND_USER_YAML = pathlib.Path(f'{FRAMEWORK.config["path_data"]}/db/flaskfarmaider.yaml')

TASK_KEYS = ('refresh_scan', 'refresh', 'scan', 'pm_ready_refresh', 'clear', 'startup', 'trash')
TASKS = {
    TASK_KEYS[0]: {'key': TASK_KEYS[0], 'name': '새로고침 후 스캔', 'desc': 'Rclone 리모트 콘트롤 서버에 vfs/refresh 요청 후 플렉스 스캔', 'enable': False},
    TASK_KEYS[1]: {'key': TASK_KEYS[1], 'name': '새로고침', 'desc': 'Rclone 리모트 콘트롤 서버에 vfs/refresh 요청', 'enable': False},
    TASK_KEYS[2]: {'key': TASK_KEYS[2], 'name': '스캔', 'desc': '플렉스 스캔을 요청', 'enable': False},
    TASK_KEYS[3]: {'key': TASK_KEYS[3], 'name': 'Plexmate Ready 새로고침', 'desc': 'Plexmate의 READY 상태인 항목들을 Rclone 리모트 서버에 vfs/refresh 요청', 'enable': False},
    TASK_KEYS[4]: {'key': TASK_KEYS[4], 'name': 'Plexmate 파일 정리', 'desc': 'Plexmate의 라이브러리 파일 정리를 일정으로 등록', 'enable': False},
    TASK_KEYS[5]: {'key': TASK_KEYS[5], 'name': '시작 스크립트', 'desc': 'Flaskfarm 시작시 필요한 OS 명령어를 실행', 'enable': False},
    TASK_KEYS[6]: {'key': TASK_KEYS[6], 'name': '휴지통 스캔', 'desc': 'Plex 이용불가 파일을 조회 후 새로고침 및 스캔', 'enable': False},
}

TOOL_TRASH_KEYS = ('trash_refresh', 'trash_scan', 'trash_empty', 'trash_refresh_scan', 'trash_refresh_scan_empty')
TOOL_TRASHES = {
    TOOL_TRASH_KEYS[0]: {'key': TOOL_TRASH_KEYS[0], 'name': '새로고침', 'desc': None},
    TOOL_TRASH_KEYS[1]: {'key': TOOL_TRASH_KEYS[1], 'name': '스캔', 'desc': None},
    TOOL_TRASH_KEYS[2]: {'key': TOOL_TRASH_KEYS[2], 'name': '비우기', 'desc': None},
    TOOL_TRASH_KEYS[3]: {'key': TOOL_TRASH_KEYS[3], 'name': '새로고침 > 스캔', 'desc': None},
    TOOL_TRASH_KEYS[4]: {'key': TOOL_TRASH_KEYS[4], 'name': '새로고침 > 스캔 > 비우기', 'desc': None},
}

STATUS_KEYS = ('ready', 'running', 'finish', 'stopping')
STATUSES = {
    STATUS_KEYS[0]: {'key': STATUS_KEYS[0], 'name': '대기', 'desc': None},
    STATUS_KEYS[1]: {'key': STATUS_KEYS[1], 'name': '실행', 'desc': None},
    STATUS_KEYS[2]: {'key': STATUS_KEYS[2], 'name': '완료', 'desc': None},
    STATUS_KEYS[3]: {'key': STATUS_KEYS[3], 'name': '중지', 'desc': None},
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

SECTION_TYPE_KEYS = ('movie', 'show', 'artist', 'photo')
SECTION_TYPES = {
    SECTION_TYPE_KEYS[0]: {'key': SECTION_TYPE_KEYS[0], 'name': '영화', 'desc': None},
    SECTION_TYPE_KEYS[1]: {'key': SECTION_TYPE_KEYS[1], 'name': 'TV', 'desc': None},
    SECTION_TYPE_KEYS[2]: {'key': SECTION_TYPE_KEYS[2], 'name': '음악', 'desc': None},
    SECTION_TYPE_KEYS[3]: {'key': SECTION_TYPE_KEYS[3], 'name': '사진', 'desc': None},
}

SETTING_DB_VERSION = f'{SETTING}_db_version'
SETTING_RCLONE_REMOTE_ADDR = f'{SETTING}_rclone_remote_addr'
SETTING_RCLONE_REMOTE_VFS = f'{SETTING}_rclone_remote_vfs'
SETTING_RCLONE_REMOTE_USER = f'{SETTING}_rclone_remote_user'
SETTING_RCLONE_REMOTE_PASS = f'{SETTING}_rclone_remote_pass'
SETTING_RCLONE_MAPPING = f'{SETTING}_rclone_remote_mapping'
SETTING_PLEXMATE_MAX_SCAN_TIME = f'{SETTING}_plexmate_max_scan_time'
SETTING_PLEXMATE_TIMEOVER_RANGE = f'{SETTING}_plexmate_timeover_range'
SETTING_PLEXMATE_PLEX_MAPPING = f'{SETTING}_plexmate_plex_mapping'
SETTING_STARTUP_EXECUTABLE = f'{SETTING}_startup_executable'
SETTING_STARTUP_COMMANDS = f'{SETTING}_startup_commands'
SETTING_STARTUP_TIMEOUT = f'{SETTING}_startup_timeout'
SETTING_STARTUP_DEPENDENCIES = f'{SETTING}_startup_dependencies'

SCHEDULE_WORKING_DIRECTORY = f'{SCHEDULE}_working_directory'
SCHEDULE_LAST_LIST_OPTION = f'{SCHEDULE}_last_list_option'

TOOL_TRASH_TASK_STATUS = f'{TOOL}_{TOOL_TRASH}_task_status'

DB_VERSIONS = ['1', '2', '3', '4']