import os
import traceback

# import time
import datetime
import re

import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "seahub.settings")
import django
django.setup()


from seaserv import seafile_api, get_repo
from seahub.settings import SERVICE_URL, SERVER_EMAIL, ARCHIVE_METADATA_TARGET
from seahub.share.models import FileShare

from seafobj import commit_mgr, fs_mgr
import subprocess
# from subprocess import STDOUT, call

from keeper.default_library_manager import get_keeper_default_library
from keeper.common import parse_markdown, get_logger

from keeper.utils import get_user_name

from keeper.models import Catalog

from django.core.mail import EmailMessage
from django.template import Context, loader


import tempfile
import json

from keeper.models import CDC
from seahub.notifications.models import UserNotification

TEMPLATE_DESC = "Template for creating 'My Libray' for users"

CDC_GENERATOR_MAIN_CLASS = "de.mpg.mpdl.keeper.CDCGenerator.MainApp"
CDC_GENERATOR_JARS =  ('CDCGenerator.jar', 'fonts-ext.jar')
CDC_PDF_PREFIX = "cared-data-certificate_"
CDC_LOGO = 'Keeper-Cared-Data-Certificate-Logo.png'
CDC_EMAIL_TEMPLATE = 'cdc_mail_template.html'
CDC_EMAIL_SUBJECT = 'Cared Data Certificate for project "%s"'
CDC_LOG = '__KEEPER_LOG_DIR__/keeper.cdc.log'

MSG_TYPE_KEEPER_CDC_MSG = 'keeper_cdc_msg'

MODULE_PATH = os.path.dirname(os.path.abspath(__file__))

logger = get_logger('keeper.cdc', CDC_LOG)

DEBUG = False

# if DEBUG:
    # logging.basicConfig(stream=sys.stdout, level=logging.INFO)

cdc_headers_mandatory =  ['Title', 'Author', 'Year', 'Description', 'Institute']
err_list = []

EVENT_PATTERNS = {
    'CDC_PDF_DELETED': re.compile(r'Deleted\s+\"' + CDC_PDF_PREFIX + r'\d+\.pdf\"$'),
    'ARCHIVE_METADATA_TARGET_MODIFIED': re.compile(r'Modified\s+\"' + ARCHIVE_METADATA_TARGET + r'\"$')
}


from enum import Enum
class EVENT(Enum):
    db_create = 1
    db_update = 2
    pdf_delete = 3
    md_modified = 4



def quote_arg(arg):
    """
    Quotes argument for shell call with subprocess
    """
    return '"%s"' % (
        arg
        .replace('\\', '\\\\')
        .replace('"', '\\"')
        .replace('$', '\\$')
        .replace('`', '\\`')
    )

def get_cdc_id_by_repo(repo_id):
    """Get cdc_id by repo_id. Return None if nothing found"""
    return CDC.objects.get_cdc_id_by_repo(repo_id)

def is_certified_by_repo_id(repo_id):
    return CDC.objects.is_certified(repo_id)

CDC_MSG = []

def validate_author(txt):
    """Author/Affiliations checking, format:
    Lastname1, Firstname1; Affiliation11, Affiliation12, ...
    Lastname2, Firstname2; Affiliation21, Affiliation22, ..
    ...
    """
    valid = True
    if txt:
        pattern = re.compile("^(\s*[\w-]+)+,(\s*[\w.-]+)+(;\s*\S+\s*)*", re.UNICODE)
        for line in txt.splitlines():
            if not re.match(pattern, line):
                valid = False
                msg = 'Wrong Author/Affiliation string: ' + line
                CDC_MSG.append(msg)
    else:
        valid = False
        msg = 'Authors are empty'
        CDC_MSG.append(msg)
    return valid

def validate_institute(txt):
    """Institute checking, format:
    InstituionName; Department; Director(or PI)Name, Vorname|Abbr.
    """
    t = txt
    t = t and t.strip()

    if not t: 
        CDC_MSG.append('Empty institution string')
        return False

    valid = True
    msg = None 

    # normalize 
    t = re.sub(r'\s+', ' ', t)
    t = re.sub(r'(\s*([;,])\s*)+', r'\g<2>', t)
    t = re.sub(r'(\s*\.\s*)+', '.', t)

    # print('txt: %s -- normalized: %s' % (t, txt))
    ins = t.strip(';').split(';')
    # print('len(ins):%s' % len(ins))

    if len(ins) >= 1:
        # Institute name
        if ins[0]:
            pattern = re.compile(r'^(\s*[\w-]+\s*)+$', re.UNICODE)
            # pattern = re.compile("^(\s*[\w-]+\s*)+?$", re.UNICODE)
            if not re.match(pattern, ins[0]):
                valid = False
                msg = 'Wrong institution name'
        else:
            valid = False
            msg = 'Institution name is empty'

        # Department name
        if len(ins) >= 2:
            if ins[1]: 
                pattern = re.compile(r'^(\s*[\w-]+\s*)+$', re.UNICODE)
                if not re.match(pattern, ins[1]):
                    valid = False
                    msg = 'Wrong department name'
            else:
                valid = False
                msg = 'Department name is empty'

            # Director name
            if len(ins) >= 3:
                if ins[2]:
                    pattern = re.compile(r'^\s*([\w-]+\s*)+?([\s,]+?([\w.-]+\s*)+?[\s;]*?)?$', re.UNICODE)
                    if not re.match(pattern, ins[2]):
                        valid = False
                        msg = 'Wrong director or PI name'
                else:
                    valid = False
                    msg = 'Director or PI name is empty'
    else:
        valid = False
        msg = 'Empty institution string'

    msg and CDC_MSG.append(msg + ': ' + txt)
     
    return valid

def validate_director(txt):
    """Institute checking, format:
    Director(or PI)Name, Vorname|Abbr.
    """
    valid = True
    if txt:                    #     Lastname       ,\s      Firstname or abbr     ;\s 
        # pattern = re.compile(r"^(\s* ([\w-]+\s*)+?  ([\s,]+? ([\w.-]+\s*)+? [\s;]*? )? )?$", re.UNICODE)
        pattern = re.compile(r"^\s*([\w-]+\s*)+?([\s,]+?([\w.-]+\s*)+?[\s;]*?)?$", re.UNICODE)
        if not re.match(pattern, txt):
            valid = False
            msg = 'Wrong director string: ' + txt
            CDC_MSG.append(msg)
    else:
        valid = False
        msg = 'Institute is empty'
        CDC_MSG.append(msg)
    return valid

def validate_year(txt):
    """Year checking"""
    valid = True
    format = "%Y"
    if txt:
        try:
            datetime.datetime.strptime(txt, format)
        except Exception:
            valid = False
            msg = 'Wrong year: ' + txt
            CDC_MSG.append(msg)
    else:
        valid = False
        msg = 'Year is empty'
        CDC_MSG.append(msg)
    return valid


def validate(cdc_dict):
    logger.info("""Validate the CDC mandatory fields and content...""")

    global CDC_MSG
    CDC_MSG = []

    # 1. check mandatory fields
    s1 = set(cdc_dict.keys())
    s2 = set(cdc_headers_mandatory)
    valid = s2.issubset(s1)
    if not valid:
        msg =  'Certificate mandatory fields are not filled: ' + ', '.join(s2.difference(s1))
        CDC_MSG.append(msg)

    # 2. check content"

    valid = validate_year(cdc_dict.get('Year')) and valid
    valid = validate_author(cdc_dict.get('Author')) and valid
    valid = validate_institute(cdc_dict.get('Institute')) and valid
    logger.info('Catalog metadata are {}:\n{}'.format('valid' if valid else 'not valid', '\n'.join(CDC_MSG)))
    return valid

def get_repo_share_url(repo_id, owner):
    """Should be repo to be certified?"""
    share = FileShare.objects.get_dir_link_by_path(owner, repo_id, "/")
    if not share:
        raise Exception('Cannot get share URL: repo is not shared')
    return SERVICE_URL + '/' + share.s_type + '/' + share.token

def get_repo_pivate_url(repo_id):
    """Get private repo url"""
    return SERVICE_URL + '/#my-libs/lib/' + repo_id

def get_file_pivate_url(repo_id, file_name):
    """Get file private url"""
    return SERVICE_URL + '/lib/' + repo_id + '/file/' + file_name


def register_cdc_in_db(repo_id, owner):
    """
    Register in DB a new certificate or update modified field if already created
    Returns certificate id and EVENT: db_create
    """
    logger.info("Register CDC in keeper-db")
    cdc_id, event = CDC.objects.register_cdc_in_db(repo_id, owner)
    logger.info("Sucessfully %s, cdc_id: %s" % ("updated" if event == EVENT.db_update else "created", cdc_id))
    return cdc_id, event

def send_email(to, msg_ctx):
    logger.info("Send CDC email and keeper notification...")
    try:
        t = loader.get_template(CDC_EMAIL_TEMPLATE)
        msg = EmailMessage(CDC_EMAIL_SUBJECT % msg_ctx['PROJECT_NAME'], t.render(msg_ctx), SERVER_EMAIL, [to, SERVER_EMAIL] )
        msg.content_subtype = "html"
        msg.attach_file(MODULE_PATH + '/' + CDC_LOGO)
        msg.send()
        logger.info("Sucessfully sent")
    except Exception:
        logger.error('Cannot send email: %s', traceback.format_exc())



def has_at_least_one_creative_dirent(dir):

    # ARCHIVE_METADATA_TARGET should be in
    check_set = set([ARCHIVE_METADATA_TARGET])

    # +KEEPER_DEFAULT_LIBRARY stuff
    kdl = get_keeper_default_library()
    if kdl:
        dirents = [d.obj_name for d in kdl['dirents']]
        if dirents:
            check_set.update(dirents)

    # get dir files
    files = dir.get_files_list()
    if files:
        files = [f for f in files if f.name not in check_set]

    # get dir dirs
    dirs = dir.get_subdirs_list()
    if dirs:
        dirs = [d for d in dirs if d.name not in check_set]

    return (len(files) + len(dirs)) > 0


def generate_certificate_by_repo(repo):
    """ Generate Cared Data Certificate by repo """

    commits = seafile_api.get_commit_list(repo.id, 0, 1)
    commit = commit_mgr.load_commit(repo.id, repo.version, commits[0].id)

    return generate_certificate(repo, commit)

def generate_certificate_by_commit(commit):
    """ Generate Cared Data Certificate by commit """

    return generate_certificate(get_repo(commit.repo_id), commit)

def get_authors_for_email(authors):
    """ Get only name, first name of author, cut affiliations """
    auths = [a.split(';')[0] for a in authors.splitlines()]
    return "; ".join(auths)

def print_OK():
    print("In cdc_manager")

def generate_certificate(repo, commit):
    """ Generate Cared Data Certificate according to markdown file """

    event = None

    # exit if repo encrypted
    if repo.encrypted:
        return False

    # exit if repo is system template
    if repo.rep_desc == TEMPLATE_DESC:
        return False

    # TODO: if cdc pdf is deleted: set cert status to False and exit
    # see https://github.com/MPDL/KEEPER/issues/41
    if re.match(EVENT_PATTERNS['CDC_PDF_DELETED'], commit.desc):
        event = EVENT.pdf_delete
        Catalog.objects.update_cert_status_by_repo_id(repo.id, False)
        return False

    if re.match(EVENT_PATTERNS['ARCHIVE_METADATA_TARGET_MODIFIED'], commit.desc):
        event = EVENT.md_modified

    try:

        cdc_id = get_cdc_id_by_repo(repo.id)

        if cdc_id is not None:
            if re.match(EVENT_PATTERNS['CDC_PDF_DELETED'], commit.desc):
                # if cdc pdf is deleted, add pdf again!
                event = EVENT.pdf_delete
            elif event != EVENT.md_modified:
                # exit if already certified and MD has not been changed
                return False

        dir = fs_mgr.load_seafdir(repo.id, repo.version, commit.root_id)

        # certificate already exists in root
        # file_names = [f.name for f in dir.get_files_list()]
        # if any(file_name.startswith(CDC_PDF_PREFIX) and file_name.endswith('.pdf') for file_name in file_names):
            # return False

        # get latest version of the ARCHIVE_METADATA_TARGET
        file = dir.lookup(ARCHIVE_METADATA_TARGET)

        #exit if no metadata file exists
        if not file:
            return False

        # check whether there is at least one creative dirent
        if not has_at_least_one_creative_dirent(dir):
            return False
        logger.info('Repo has creative dirents')

        owner = seafile_api.get_repo_owner(repo.id)
        logger.info("Certifying repo id: %s, name: %s, owner: %s ..." % (repo.id, repo.name, owner))
        content = file.get_content().decode('utf-8')
        cdc_dict = parse_markdown(content)

        status = 'metadata are not valid'
        is_successful = False

        if validate(cdc_dict):

            status = 'metadata are valid'

            if event == EVENT.pdf_delete:
                # only modified update
                cdc_id = register_cdc_in_db(repo.id, owner)[0]
            else:
                cdc_id, event = register_cdc_in_db(repo.id, owner)

            cdc_id = str(cdc_id)
            logger.info("Generate CDC PDF...")
            cdc_pdf =  CDC_PDF_PREFIX + cdc_id + ".pdf"
            jars = ":".join([MODULE_PATH + '/' + e for e in CDC_GENERATOR_JARS])
            tmp_path = tempfile.gettempdir() + "/" + cdc_pdf
            args = [ "date;",
                    "java", "-cp", jars, CDC_GENERATOR_MAIN_CLASS,
                    "-i", quote_arg(cdc_id),
                    "-t", quote_arg(cdc_dict['Title']),
                    "-aa", quote_arg(cdc_dict['Author']),
                    "-d", quote_arg(cdc_dict['Description']),
                    "-c", quote_arg(owner),
                    "-u", quote_arg(SERVICE_URL),
                    tmp_path,
                    "1>&2;",
                    ]
            try:
                call_str = " ".join(args)
                logger.info(call_str)
                # subprocess.call(call_str, shell=True)
                # p = subprocess.Popen(call_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p = subprocess.Popen(call_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                stdout, stderr = p.communicate()
                if stdout:
                    logger.info(stdout)
                if stderr:
                    logger.error(stderr)

            except Exception as err:
                logger.error('Cannot call command')
                logger.error(traceback.format_exc())
                raise err

            if os.path.isfile(tmp_path):
                logger.info("PDF sucessfully generated, tmp_path=%s" % tmp_path)
            else:
                logger.error("Cannot find generated CDC PDF, tmp_path=%s, exiting..." % tmp_path)
                if event == EVENT.db_create:
                    # TODO: test
                    CDC.objects.get(cdc_id=cdc_id).delete()
                return False

            logger.info("Add " + cdc_pdf + " to the repo...")
            if event == EVENT.db_update:
                # cdc pdf already exists, then put
                if dir.lookup(cdc_pdf):
                    seafile_api.put_file(repo.id, tmp_path, "/", cdc_pdf, SERVER_EMAIL, None)
                    logger.info("Sucessfully updated")
                    status = 'updated'
                    CDC_MSG.append("Certificate has been updated")
                # post otherwise
                else:
                    seafile_api.post_file(repo.id, tmp_path, "/", cdc_pdf, SERVER_EMAIL)
                    logger.info("Sucessfully recreated")
                    status = 'recreated'
                    CDC_MSG.append("Certificate has been recreated")
                logging.info("CDC has been successfully updated for repo %s, id: %s" % (repo.id, cdc_id) )
            else:
                seafile_api.post_file(repo.id, tmp_path, "/", cdc_pdf, SERVER_EMAIL)
                logger.info("Sucessfully created")
                status = 'created'
                CDC_MSG.append("Certificate has been sucessfully created")
                # if not DEBUG:
                send_email(owner, {'SERVICE_URL': SERVICE_URL, 'USER_NAME': get_user_name(owner), 'PROJECT_NAME': repo.name,
                    'PROJECT_TITLE': cdc_dict['Title'], 'PROJECT_URL': get_repo_pivate_url(repo.id),
                    'AUTHOR_LIST': get_authors_for_email(cdc_dict['Author']), 'CDC_PDF_URL': get_file_pivate_url(repo.id, cdc_pdf), 'CDC_ID': cdc_id })
                logging.info("CDC has been successfully created for repo %s, id: %s" % (repo.id, cdc_id) )

            is_successful = True

        #send user notification
        logger.info("Commit desc: " + commit.desc)
        logger.info("event: {}".format(event))
        if event in (EVENT.md_modified, EVENT.db_create, EVENT.db_update):
            header = "Certificate processed for library" if is_successful else "Cannot process certificate for library"
            UserNotification.objects._add_user_notification(owner, MSG_TYPE_KEEPER_CDC_MSG,
                json.dumps({
                'header': header,
                'status': status,
                'message':('; '.join(CDC_MSG)),
                'msg_from': SERVER_EMAIL,
                'lib': repo.id,
                'lib_name': repo.name
            }))

    except Exception as err:
        logger.error(traceback.format_exc())
        logging.error("CDC generation for repo %s has been failed, check %s for details. \nTraceback:" % (repo.id, CDC_LOG) )
        logging.error(traceback.format_exc())
    finally:
        if 'tmp_path' in vars() and os.path.exists(tmp_path):
            os.remove(tmp_path)

    return True

"""
if DEBUG:
    print get_user_name('vlamak868@gmail.com')
    repo = seafile_api.get_repo('eba0b70c-8d20-4949-841b-29f13c5246fd')
    commits = seafile_api.get_commit_list(repo.id, 0, 1)
    commit = commit_mgr.load_commit(repo.id, repo.version, commits[0].id)
    dir = fs_mgr.load_seafdir(repo.id, repo.version, commit.root_id)
    print has_at_least_one_creative_dirent(dir)

    repo = seafile_api.get_repo('a6d4ae75-b063-40bf-a3d9-dde74623bb2c')
    generate_certificate_by_repo(repo)
    pattern = re.compile(r'Modified\s+\"' + CDC_PDF_PREFIX +  r'\d+\.pdf\"$')
    print re.match(pattern, r'Modified "cared-data-certificate_2004.pdf"')

    send_email('vlamak868@gmail.com', {'USER_NAME': '__USER_NAME__', 'PROJECT_NAME':'repo.name', 'PROJECT_TITLE': '___project__title___', 'PROJECT_URL':'_PROJECT_URL_', 'AUTHOR_LIST':'__AUTHOR_LIST__', 'CDC_PDF_URL': '_CDC_PDF_URL_', 'CDC_ID': '__CDC_id__' })
"""
