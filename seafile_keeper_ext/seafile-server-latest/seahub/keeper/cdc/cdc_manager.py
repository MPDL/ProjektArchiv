# -*- coding: utf-8 -*-

import os
import traceback

# import time
import datetime
import re

import logging

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "seahub.settings")

from seaserv import seafile_api, get_repo
from seahub.settings import SERVICE_URL, SERVER_EMAIL, ARCHIVE_METADATA_TARGET
from seahub.share.models import FileShare

from seafobj import commit_mgr, fs_mgr
import subprocess
# from subprocess import STDOUT, call

from keeper.default_library_manager import get_keeper_default_library
from keeper.common import parse_markdown, get_user_name, get_logger

from django.core.mail import EmailMessage
from django.template import Context, loader

from keeper.models import CDC

import tempfile

TEMPLATE_DESC = u"Template for creating 'My Libray' for users"

CDC_GENERATOR_MAIN_CLASS = "de.mpg.mpdl.keeper.CDCGenerator.MainApp"
CDC_GENERATOR_JARS =  ('CDCGenerator.jar', 'fonts-ext.jar')
CDC_PDF_PREFIX = "cared-data-certificate_"
CDC_LOGO = 'Keeper-Cared-Data-Certificate-Logo.png'
CDC_EMAIL_TEMPLATE = 'cdc_mail_template.html'
CDC_EMAIL_SUBJECT = 'Cared Data Certificate for project "%s"'
CDC_LOG = '/var/log/keeper/keeper.cdc.log'

MODULE_PATH = os.path.dirname(os.path.abspath(__file__))

LOGGER = get_logger('keeper.cdc', CDC_LOG)

DEBUG = False

# if DEBUG:
    # logging.basicConfig(stream=sys.stdout, level=logging.INFO)

cdc_headers_mandatory =  ['Title', 'Author', 'Year', 'Description', 'Institute']
err_list = []

from enum import Enum
class EVENT(Enum):
    db_create = 1
    db_update = 2
    pdf_delete = 3



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

DEBUG_MESSAGE = []

def validate_author(txt):
    """Author/Affiliations checking, format:
    Lastname1, Firstname1; Affiliation11, Affiliation12, ...
    Lastname2, Firstname2; Affiliation21, Affiliation22, ..
    ...
    """
    valid = True
    if txt:
        pattern = re.compile("^\s*[\w-]+,(\s*[\w.-]+)+(;\s*\S+\s*)*", re.UNICODE)
        for line in txt.splitlines():
            if not re.match(pattern, line.decode('utf-8')):
                valid = False
                msg = 'Wrong Author/Affiliation string: ' + line
                DEBUG_MESSAGE.append(msg)
                LOGGER.error(msg)
    else:
        valid = False
        msg = 'Authors are empty'
        DEBUG_MESSAGE.append(msg)
        LOGGER.info(msg)
    return valid

def validate_institute(txt):
    """Institute checking, format:
    InstituionName; Department; Director(or PI)Name, Vorname|Abbr.
    """
    valid = True
    if txt:                    # Institution      Department        Director
        pattern = re.compile("^(\s*[\w-]+\s*[;]*)+?((;\s*[\w-]+\s*)??(;\s*([\w-]+\s*)+?([\s,]+?([\w.-]+\s*)+?)??[\s;]*)??)?$", re.UNICODE)
        # pattern = re.compile("^(\s*[\w-]+\s*)+?$", re.UNICODE)
        if not re.match(pattern, txt.decode('utf-8')):
            valid = False
            msg = 'Wrong Institution string: ' + txt
            DEBUG_MESSAGE.append(msg)
            LOGGER.error(msg)
    else:
        valid = False
        msg = 'Institute is empty'
        DEBUG_MESSAGE.append(msg)
        LOGGER.info(msg)
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
            DEBUG_MESSAGE.append(msg)
            LOGGER.error(msg)
    else:
        valid = False
        msg = 'Year is empty'
        DEBUG_MESSAGE.append(msg)
        LOGGER.info(msg)
    return valid


def validate(cdc_dict):
    LOGGER.info("""Validate the CDC mandatory fields and content...""")
    global DEBUG_MESSAGE
    # 1. check mandatory fields
    s1 = set(cdc_dict.keys())
    s2 = set(cdc_headers_mandatory)
    valid = s2.issubset(s1)
    if not valid:
        msg =  'CDC mandatory fields are not filled: ' + ', '.join(s2.difference(s1))
        DEBUG_MESSAGE.append(msg)
        LOGGER.info(msg)

    # 2. check content"

    valid = validate_year(cdc_dict.get('Year')) and valid
    valid = validate_author(cdc_dict.get('Author')) and valid
    valid = validate_institute(cdc_dict.get('Institute')) and valid

    LOGGER.info('valid' if valid else 'not valid')
    print 'Validation errors: ' + '<br>'.join(DEBUG_MESSAGE)
    DEBUG_MESSAGE = []

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
    LOGGER.info("Register CDC in keeper-db")
    cdc_id, event = CDC.objects.register_cdc_in_db(repo_id, owner)
    LOGGER.info("Sucessfully %s, cdc_id: %s" % ("updated" if event == EVENT.db_update else "created", cdc_id) )
    return cdc_id, event

def send_email(to, msg_ctx):
    LOGGER.info("Send CDC email and keeper notification...")
    try:
        t = loader.get_template(CDC_EMAIL_TEMPLATE)
        msg = EmailMessage(CDC_EMAIL_SUBJECT % msg_ctx['PROJECT_NAME'], t.render(Context(msg_ctx)), SERVER_EMAIL, [to, SERVER_EMAIL] )
        msg.content_subtype = "html"
        msg.attach_file(MODULE_PATH + '/' + CDC_LOGO)
        msg.send()
    except Exception as err:
        LOGGER.error('Cannot send email')
        raise err

    LOGGER.info("Sucessfully sent")

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
    print "In cdc_manager"

def generate_certificate(repo, commit):
    """ Generate Cared Data Certificate according to markdown file """

    event = None

    # exit if repo encrypted
    if repo.encrypted:
        return False

    # exit if repo is system template
    if repo.rep_desc == TEMPLATE_DESC:
        return False

    # exit if cdc pdf is deleted
    # see https://github.com/MPDL/KEEPER/issues/41
    pattern = re.compile(r'Deleted\s+\"' + CDC_PDF_PREFIX + r'\d+\.pdf\"$')
    if re.match(pattern, commit.desc):
        return False

    try:

        cdc_id = get_cdc_id_by_repo(repo.id)
        if cdc_id is not None:
            pattern = re.compile(r'Deleted\s+\"' + CDC_PDF_PREFIX + r'\d+\.pdf\"$')
            if re.match(pattern, commit.desc):
                # if cdc pdf is deleted, add pdf again!
                event = EVENT.pdf_delete
            else:
                pattern = re.compile(r'Modified\s+\"' + ARCHIVE_METADATA_TARGET + r'\"$')
                if not re.match(pattern, commit.desc):
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
        LOGGER.info('Repo has creative dirents')

        owner = seafile_api.get_repo_owner(repo.id)
        LOGGER.info("Certifying repo id: %s, name: %s, owner: %s ..." % (repo.id, repo.name, owner))
        cdc_dict = parse_markdown(file.get_content())
        if validate(cdc_dict):

            if event == EVENT.pdf_delete:
                # only modified update
                cdc_id = register_cdc_in_db(repo.id, owner)[0]
            else:
                cdc_id, event = register_cdc_in_db(repo.id, owner)

            cdc_id = str(cdc_id)
            LOGGER.info("Generate CDC PDF...")
            cdc_pdf =  CDC_PDF_PREFIX + cdc_id + ".pdf"
            jars = ":".join(map(lambda e : MODULE_PATH + '/' + e, CDC_GENERATOR_JARS))
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
                call_str = " ".join([s.decode('utf-8') for s in args])
                LOGGER.info(call_str)
                # subprocess.call(call_str, shell=True)
                # p = subprocess.Popen(call_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p = subprocess.Popen(call_str, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                stdout, stderr = p.communicate()
                if stdout:
                    LOGGER.info(stdout)
                if stderr:
                    LOGGER.error(stderr)

            except Exception as err:
                LOGGER.error('Cannot call command')
                LOGGER.error(traceback.format_exc())
                raise err

            if os.path.isfile(tmp_path):
                LOGGER.info("PDF sucessfully generated, tmp_path=%s" % tmp_path)
            else:
                LOGGER.error("Cannot find generated CDC PDF, tmp_path=%s, exiting..." % tmp_path)
                if event == EVENT.db_create:
                    # TODO: test it!
                    CDC.objects.get(cdc_id=cdc_id).delete()
                return False

            LOGGER.info("Add " + cdc_pdf + " to the repo...")
            if event == EVENT.db_update:
                # cdc pdf already exists, then put
                if dir.lookup(cdc_pdf):
                    seafile_api.put_file(repo.id, tmp_path, "/", cdc_pdf, SERVER_EMAIL, None)
                    LOGGER.info("Sucessfully updated")
                # post otherwise
                else:
                    seafile_api.post_file(repo.id, tmp_path, "/", cdc_pdf, SERVER_EMAIL)
                    LOGGER.info("Sucessfully recreated")
                logging.info("CDC has been successfully updated for repo %s, id: %s" % (repo.id, cdc_id) )
            else:
                seafile_api.post_file(repo.id, tmp_path, "/", cdc_pdf, SERVER_EMAIL)
                LOGGER.info("Sucessfully created")
                # if not DEBUG:
                send_email(owner, {'SERVICE_URL': SERVICE_URL, 'USER_NAME': get_user_name(owner), 'PROJECT_NAME': repo.name,
                    'PROJECT_TITLE': cdc_dict['Title'], 'PROJECT_URL': get_repo_pivate_url(repo.id),
                    'AUTHOR_LIST': get_authors_for_email(cdc_dict['Author']), 'CDC_PDF_URL': get_file_pivate_url(repo.id, cdc_pdf), 'CDC_ID': cdc_id })
                logging.info("CDC has been successfully created for repo %s, id: %s" % (repo.id, cdc_id) )



    except Exception as err:
        LOGGER.error(traceback.format_exc())
        logging.error("CDC generation for repo %s has been failed, check %s for details. \nTraceback:" % (repo.id, CDC_LOG) )
        logging.error(traceback.format_exc())
    finally:
       # other final stuff
        if not DEBUG:
            if 'tmp_path' in vars() and os.path.exists(tmp_path):
                os.remove(tmp_path)

    return True


# test
if DEBUG:
    event = EVENT.db_update
    print event
    """
    print get_user_name('vlamak868@gmail.com')
    repo = seafile_api.get_repo('eba0b70c-8d20-4949-841b-29f13c5246fd')
    commits = seafile_api.get_commit_list(repo.id, 0, 1)
    commit = commit_mgr.load_commit(repo.id, repo.version, commits[0].id)
    dir = fs_mgr.load_seafdir(repo.id, repo.version, commit.root_id)
    print has_at_least_one_creative_dirent(dir)
    """
    """
    repo = seafile_api.get_repo('a6d4ae75-b063-40bf-a3d9-dde74623bb2c')
    generate_certificate_by_repo(repo)
    pattern = re.compile(r'Modified\s+\"' + CDC_PDF_PREFIX +  r'\d+\.pdf\"$')
    print re.match(pattern, r'Modified "cared-data-certificate_2004.pdf"')
    """
    """
    send_email('vlamak868@gmail.com', {'USER_NAME': '__USER_NAME__', 'PROJECT_NAME':'repo.name', 'PROJECT_TITLE': '___project__title___', 'PROJECT_URL':'_PROJECT_URL_', 'AUTHOR_LIST':'__AUTHOR_LIST__', 'CDC_PDF_URL': '_CDC_PDF_URL_', 'CDC_ID': '__CDC_id__' })
    """
