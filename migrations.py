import sqlite3

from .setup import LOGGER
from .constants import TASK_KEYS, SCAN_MODE_KEYS


def migrate(ver: str, table, cs: sqlite3.Cursor) -> None:
    if ver == '1':
        migrate_v2(cs, table)
    elif ver == '2':
        migrate_v3(cs, table)
    elif ver == '3':
        migrate_v4(cs, table)


def migrate_v2(cs: sqlite3.Cursor, table: str) -> None:
    LOGGER.debug('DB 버전 2 로 마이그레이션')
    # check old table
    old_table_rows = cs.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='job'").fetchall()
    if old_table_rows[0]['count(*)']:
        LOGGER.debug('old table exists!')
        cs.execute(f'ALTER TABLE "job" RENAME TO "job_OLD_TABLE"').fetchall()
        new_table_rows = cs.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{table}'").fetchall()
        if new_table_rows[0]['count(*)']:
            # drop new blank table
            LOGGER.debug('new blank table exists!')
            cs.execute(f'DROP TABLE {table}').fetchall()
        # rename table
        cs.execute(f'ALTER TABLE "job_OLD_TABLE" RENAME TO "{table}"').fetchall()

        # add/drop columns
        rows = cs.execute(f'SELECT name FROM pragma_table_info("{table}")').fetchall()
        cols = [row['name'] for row in rows]
        if 'commands' in cols:
            cs.execute(f'ALTER TABLE "{table}" DROP COLUMN "commands"').fetchall()
        if 'scan_mode' not in cols:
            cs.execute(f'ALTER TABLE "{table}" ADD COLUMN "scan_mode" VARCHAR').fetchall()
        if 'periodic_id' not in cols:
            cs.execute(f'ALTER TABLE "{table}" ADD COLUMN "periodic_id" INTEGER').fetchall()

        # check before seting values
        rows = cs.execute(f'SELECT name FROM pragma_table_info("{table}")').fetchall()
        cols = [row['name'] for row in rows]
        LOGGER.debug(f'table cols: {cols}')
        rows = cs.execute(f'SELECT * FROM "{table}"').fetchall()
        for row in rows:
            LOGGER.debug(f"{row['id']} | {row['ctime']} | {row['task']} | {row['desc']} | {row['target']} | {row['scan_mode']} | {row['periodic_id']}")

        LOGGER.debug('========== set values ==========')

        # set values
        rows = cs.execute(f'SELECT * FROM "{table}"').fetchall()
        for row in rows:
            if not row['scan_mode']:
                cs.execute(f'UPDATE {table} SET scan_mode = "plexmate" WHERE id = {row["id"]}').fetchall()
            if not row['periodic_id']:
                cs.execute(f'UPDATE {table} SET periodic_id = -1 WHERE id = {row["id"]}').fetchall()

            if row['task'] == 'refresh':
                pass
            elif row['task'] == 'scan':
                # Plex Web API로 스캔 요청
                cs.execute(f'UPDATE {table} SET scan_mode = "web" WHERE id = {row["id"]}').fetchall()
            elif row['task'] == 'startup':
                pass
            elif row['task'] == 'pm_scan':
                # Plexmate로 스캔 요청
                cs.execute(f'UPDATE {table} SET task = "scan" WHERE id = {row["id"]}').fetchall()
            elif row['task'] == 'pm_ready_refresh':
                # Plexmate Ready 새로고침
                pass
            elif row['task'] == 'refresh_pm_scan':
                # 새로고침 후 Plexmate 스캔
                cs.execute(f'UPDATE {table} SET task = "refresh_scan" WHERE id = {row["id"]}').fetchall()
                pass
            elif row['task'] == 'refresh_pm_periodic':
                # 새로고침 후 주기적 스캔
                cs.execute(f'UPDATE {table} SET task = "refresh_scan" WHERE id = {row["id"]}').fetchall()
                cs.execute(f'UPDATE {table} SET scan_mode = "periodic" WHERE id = {row["id"]}').fetchall()
                cs.execute(f'UPDATE {table} SET periodic_id = {int(row["target"])} WHERE id = {row["id"]}').fetchall()
                cs.execute(f'UPDATE {table} SET target = "" WHERE id = {row["id"]}').fetchall()
            elif row['task'] == 'refresh_scan':
                # 새로고침 후 웹 스캔
                cs.execute(f'UPDATE {table} SET scan_mode = "web" WHERE id = {row["id"]}').fetchall()

        # final check
        rows = cs.execute(f'SELECT * FROM "{table}"').fetchall()
        for row in rows:
            LOGGER.debug(f"{row['id']} | {row['ctime']} | {row['task']} | {row['desc']} | {row['target']} | {row['scan_mode']} | {row['periodic_id']}")
            #print(dict(row))
            if not row['task'] in TASK_KEYS:
                LOGGER.error(f'wrong task: {row["task"]}')
            if not row['scan_mode'] in SCAN_MODE_KEYS:
                LOGGER.error(f'wrong scan_mode: {row["scan_mode"]}')


def migrate_v3(cs: sqlite3.Cursor, table: str) -> None:
    LOGGER.debug('DB 버전 3 로 마이그레이션')
    rows = cs.execute(f'SELECT name FROM pragma_table_info("{table}")').fetchall()
    cols = [row['name'] for row in rows]
    if 'clear_type' not in cols:
        cs.execute(f'ALTER TABLE "{table}" ADD COLUMN "clear_type" VARCHAR').fetchall()
    if 'clear_level' not in cols:
        cs.execute(f'ALTER TABLE "{table}" ADD COLUMN "clear_level" VARCHAR').fetchall()
    if 'clear_section' not in cols:
        cs.execute(f'ALTER TABLE "{table}" ADD COLUMN "clear_section" INTEGER').fetchall()


def migrate_v4(cs: sqlite3.Cursor, table: str) -> None:
    LOGGER.debug('DB 버전 4 로 마이그레이션')
    try:
        cs.execute(f'ALTER TABLE "{table}" DROP COLUMN "journal"').fetchall()
    except Exception as e:
        LOGGER.error(e)
