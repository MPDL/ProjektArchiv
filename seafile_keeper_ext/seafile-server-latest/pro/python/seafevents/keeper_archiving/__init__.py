import os
import re
import logging
import subprocess

from seafevents.utils import run, get_python_executable
from seahub.settings import SEAFILE_DIR
from urllib import parse

__all__ = [
    'KeeperArchiving',
]
logger = logging.getLogger(__name__)

REPO_ID_PATTERN = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
def _valid_repo_id(repo_id):
    return REPO_ID_PATTERN.match(str(repo_id)) is not None

class KeeperArchiving(object):

    def __init__(self, conf):

        self._enabled = conf['enabled']

        if self._enabled:
            self._host = conf['host']
            self._port = conf['port']
            self._local_storage = conf['local_storage']
            self._workers = conf['workers']
            self._archive_max_size = conf['archive-max-size']
            self._archives_per_library = conf['archives-per-library']
            self._hpss_enabled = conf['hpss_enabled']
            self._hpss_url = conf['hpss_url']
            self._hpss_user = conf['hpss_user']
            self._hpss_password = conf['hpss_password']
            self._hpss_storage_path = conf['hpss_storage_path']

            self._archiving_server_proc = None
            self._archiving_server_py = os.path.join(os.path.dirname(__file__), 'archiving_server.py')

            self._logfile = conf['log_directory'] + '/keeper.archiving.log'


    def start(self):
        INSTALLPATH = SEAFILE_DIR  + '/seafile-server-latest'

        pp = [INSTALLPATH + p for p in (
            '/seafile/lib/python3.6/site-packages',
            '/seahub/thirdpart',
            '/seahub',
            '/seahub-extra',
            '/pro/python'
        )]
        env = {
            'CCNET_CONF_DIR': SEAFILE_DIR + '/ccnet',
            'SEAFILE_CONF_DIR': SEAFILE_DIR + '/seafile-data',
            'SEAFILE_CENTRAL_CONF_DIR': SEAFILE_DIR + '/conf',
            'SEAFES_DIR': INSTALLPATH + '/pro/python/seafes',
            'SEAHUB_DIR': INSTALLPATH + '/seahub',
            'SEAHUB_LOG_DIR': SEAFILE_DIR + '/logs',
            'SEAFILE_RPC_PIPE_PATH': INSTALLPATH + '/runtime',
            'PYTHONPATH': ':'.join(pp)
        }

        split = parse.urlsplit(self._host)
        host = split.path if not split.scheme else split.netloc

        archiving_server_args = [
            get_python_executable(),
            self._archiving_server_py,
            '--host',
            host,
            '--port',
            self._port,
            '--local_storage',
            self._local_storage,
            '--workers',
            self._workers,
            '--archive_max_size',
            self._archive_max_size,
            '--archives_per_library',
            self._archives_per_library,
            '--hpss_enabled',
            self._hpss_enabled,
            '--hpss_url',
            self._hpss_url,
            '--hpss_user',
            self._hpss_user,
            '--hpss_password',
            self._hpss_password,
            '--hpss_storage_path',
            self._hpss_storage_path,
        ]

        with open(self._logfile, 'a') as fp:
            self._archiving_server_proc = run(
                archiving_server_args, env=env, cwd=os.path.dirname(__file__), output=fp
            )

        exists_args = ["ps", "-ef"]
        result = run(exists_args, output=subprocess.PIPE)
        rows = result.stdout.read().decode('utf-8')
        if self._archiving_server_py in rows:
            logging.info('Keeper archiving http server is already started.')
        else:
            logging.warning('Failed to start keeper archiving http server.')

        logging.info('Keeper archiving is started.')

    def stop(self):
        if self._archiving_server_proc:
            try:
                self._archiving_server_proc.terminate()
                logging.info('Keeper archiving http server is stopped.')
            except Exception as e:
                logger.error(e)
                logging.error('Cannot stop keeper archiving http server.')
                pass

    def is_enabled(self):
        return self._enabled


