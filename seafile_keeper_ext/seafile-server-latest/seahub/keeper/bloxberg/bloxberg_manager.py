import logging
from seahub.api2.utils import json_response
from seahub import settings

from keeper.catalog.catalog_manager import get_catalog

from django.http import JsonResponse
import sys
import hashlib
from seafobj import commit_mgr, fs_mgr
from seaserv import seafile_api, get_repo

import time

from keeper.models import BCertificate
from seahub.notifications.models import UserNotification
import json
from seahub.base.templatetags.seahub_tags import email2nickname
from seahub.utils import send_html_email, get_site_name
from django.utils.translation import ugettext as _

# Get an instance of a logger
logger = logging.getLogger(__name__)

MSG_TYPE_KEEPER_BLOXBERG_MSG = 'bloxberg_msg'

def hash_file(repo_id, path, user_email):
    file = get_file_by_path(repo_id, path)
    BUF_SIZE = 65536  # lets read stuff in 64kb chunks!
    file_hash_inc = hashlib.sha256()
    stream = file.get_stream()

    while True:
        data = stream.read(BUF_SIZE)
        if not data:
            break
        file_hash_inc.update(data);

    data = {
        'certifyVariables': {
            'checksum': file_hash_inc.hexdigest(),
            'authorName': email2nickname(user_email),
            'timestampString': str(time.time()),
        }
    }
    return data

def get_file_by_path(repo_id, path):
    repo = seafile_api.get_repo(repo_id)
    dir = fs_mgr.load_seafdir(repo.id, repo.version, get_commit_root_id(repo_id))
    paths = [_f for _f in path.split("/") if _f]
    for path in paths:
        dir = dir.lookup(path)
    return dir

def get_commit_id(repo_id):
    repo = seafile_api.get_repo(repo_id)
    commits = seafile_api.get_commit_list(repo.id, 0, 1)
    return commits[0].id

def get_commit_root_id(repo_id):
    repo = seafile_api.get_repo(repo_id)
    commits = seafile_api.get_commit_list(repo.id, 0, 1)
    commit = commit_mgr.load_commit(repo.id, repo.version, commits[0].id)
    return commit.root_id

def create_bloxberg_certificate(repo_id, path, transaction_id, created_time, checksum, user_email):
    commit_id = get_commit_id(repo_id)
    obj_id =  BCertificate.objects.add_bloxberg_certificate(transaction_id, repo_id, path, commit_id, created_time, user_email, checksum)
    send_notification(repo_id, path, transaction_id, created_time, user_email)
    return obj_id

def certified_with_keeper(repo_id, path):
    commit_id = get_commit_id(repo_id)
    return BCertificate.objects.has_bloxberg_certificate(repo_id, path, commit_id)

def send_notification(repo_id, path, transaction_id, timestamp, user_email):
    BLOXBERG_MSG=[]
    msg = 'Your data was successfully certified!'
    msg_transaction = 'Transaction ID: ' + transaction_id
    file_name = path.rsplit('/', 1)[-1]
    BLOXBERG_MSG.append(msg)
    BLOXBERG_MSG.append(msg_transaction)

    UserNotification.objects._add_user_notification(user_email, MSG_TYPE_KEEPER_BLOXBERG_MSG,
      json.dumps({
      'message':('; '.join(BLOXBERG_MSG)),
      'transaction_id': transaction_id,
      'repo_id': repo_id,
      'link_to_file': path,
      'file_name': file_name,
      'author_name': email2nickname(user_email),
    }))

    c = {
        'to_user': user_email,
        'message_type': 'bloxberg_msg',
        'message':('; '.join(BLOXBERG_MSG)),
        'transaction_id': transaction_id,
        'repo_id': repo_id,
        'link_to_file': path,
        'file_name': file_name,
        'author_name': email2nickname(user_email),
        'timestamp': timestamp,
    }

    try:
        send_html_email(_('New notice on %s') % get_site_name(),
                                'notifications/keeper_email.html', c,
                                None, [user_email])

        logger.info('Successfully sent email to %s' % user_email)
    except Exception as e:
        logger.error('Failed to send email to %s, error detail: %s' % (user_email, e))
