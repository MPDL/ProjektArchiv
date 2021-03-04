# -*- coding: utf-8 -*-
import logging
import re
import json
from seafobj import commit_mgr, fs_mgr
from seaserv import seafile_api, get_repo
from seahub.api2.utils import json_response
from seahub.settings import SERVICE_URL, SERVER_EMAIL, ARCHIVE_METADATA_TARGET
from keeper.common import parse_markdown_doi
from keeper.cdc.cdc_manager import validate_year, validate_author, validate_institute, has_at_least_one_creative_dirent
from seahub.notifications.models import UserNotification
from seahub.utils import send_html_email, get_site_name
from django.utils.translation import ugettext as _
from seafevents.keeper_archiving.db_oper import MSG_TYPE_KEEPER_ARCHIVING_MSG

# Get an instance of a logger
LOGGER = logging.getLogger(__name__)
TEMPLATE_DESC = "Template for creating 'My Libray' for users"
MSG_TYPE_KEEPER_DOI_MSG = "doi_msg"
MSG_TYPE_KEEPER_DOI_SUC_MSG = "doi_suc_msg"
MSG_TYPE_INVALID_METADATA_MSG = "invalid_metadata_msg"

PUBLISHER = 'MPDL Keeper Service, Max-Planck-Gesellschaft zur Förderung der Wissenschaften e. V.'
RESOURCE_TYPE = 'Library'

def get_metadata(repo_id, user_email, action_type):
    """ Read metadata from libray root folder"""

    repo = seafile_api.get_repo(repo_id)
    commit_id = get_latest_commit_root_id(repo)

    notification_type = MSG_TYPE_KEEPER_DOI_MSG if action_type == "assign DOI" else MSG_TYPE_KEEPER_ARCHIVING_MSG
    # exit if repo is system template
    if repo.rep_desc == TEMPLATE_DESC:
        msg = _('Cannot ' + action_type + ' if the library is system template destination.')
        send_notification(msg, repo_id, notification_type, user_email)
        return {
            'error': msg,
        }

    if seafile_api.get_repo_history_limit(repo_id) > -1:
        msg = _('Cannot ' + action_type +' because of the histroy setting.')
        send_notification(msg, repo_id, notification_type, user_email)
        return {
            'error': msg,
        }

    try:
        dir = fs_mgr.load_seafdir(repo.id, repo.version, commit_id)
        if not has_at_least_one_creative_dirent(dir):
            msg = _('Cannot ' + action_type +' if the library has no content.')
            send_notification(msg, repo_id, notification_type, user_email)
            return {
                'error': msg,
            }
        LOGGER.info('Repo has content')

        file = dir.lookup(ARCHIVE_METADATA_TARGET)
        if not file:
            msg = _('Cannot ' + action_type +' if archive-metadata.md file is not filled or missing.')
            send_notification(msg, repo_id, notification_type, user_email)
            return {
                'error': msg,
            }
        owner = seafile_api.get_repo_owner(repo.id)
        LOGGER.info("Assigning DOI for repo id: {}, name: {}, owner: {} ...".format(repo.id, repo.name, owner))
        doi_dict = parse_markdown_doi(file.get_content().decode())
        ## Add hardcoded DOI metadata
        ## TODO: will be editable in next DOI releases
        doi_dict.update({
            'Publisher': PUBLISHER,
            'Resource Type': RESOURCE_TYPE
        })
        LOGGER.info(doi_dict)

        doi_msg = validate(doi_dict, repo_id, user_email)
        if len(doi_msg) > 0:
            return {
                'error': ' '.join(doi_msg) + ' ' + _('Please check out notifications for more details.'),
            }
        return doi_dict

    except Exception as err:
        LOGGER.error(str(err))
        raise err

def generate_metadata_xml(doi_dict):
    """ DataCite Metadata Generator """
    kernelNamespace = "http://datacite.org/schema/kernel-4"
    kernelSchema = "http://schema.datacite.org/meta/kernel-4/metadata.xsd"
    kernelSchemaLocation = kernelNamespace + " " + kernelSchema

    publisher = "MPDL Keeper Service, Max-Planck-Gesellschaft zur Förderung der Wissenschaften e. V."
    resource_type = "Library"

    title = process_special_char(doi_dict.get('Title'))
    creators = process_special_char(doi_dict.get('Author'))
    LOGGER.info(creators)
    LOGGER.info(str.splitlines(creators))
    description = process_special_char(doi_dict.get('Description'))
    publisher = doi_dict.get('Publisher')
    year = doi_dict.get('Year')
    resource_type = doi_dict.get('Resource Type')
    prev_doi = None

    header = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>" + br() + "<resource xmlns=\"" + kernelNamespace + "\" xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xsi:schemaLocation=\"" + kernelSchemaLocation + "\">" + br()
    xml = header
    # Mandatory Elements: Title(s), Creator(s), Publisher, PublicationYear, resourceType, descriptions, resource(is it optional)
    # NameIdentifier, affiliation is not used
    xml += ota("identifier", attrib("identifierType", "DOI")) + ct("identifier") +br()
    xml += ot("titles") + br() + tab(1) + ot("title") + title + ct("title") + br() + ct("titles") + br()
    xml += generate_creators_xml(creators)
    xml += ot("publisher") + publisher + ct("publisher") + br()
    xml += ot("publicationYear") + year + ct("publicationYear") + br()
    xml += ota("resourceType", attrib("resourceTypeGeneral", "Dataset")) + resource_type + ct("resourceType") + br()
    xml += ot("descriptions") + br() + tab(1) + ota("description", attrib("descriptionType", "Abstract")) + description + ct("description") + br() + ct("descriptions") + br()
    if prev_doi is not None:
        xml += ot("relatedIdentifiers") +br() + tab(1) + ota("relatedIdentifier", attrib("relatedIdentifierType", "DOI") + " " + attrib("relationType", "IsNewVersionOf")) + prev_doi + ct("relatedIdentifierType") + br() + ct("relatedIdentifiers") + br()
    xml += ct("resource")
    LOGGER.info(xml)
    return xml

def generate_creators_xml(authors):
    xml = ot("creators") + br()
    for author in authors.splitlines():
        author_array = author.split(";")
        creator_name = author_array[0]
        xml += tab(1) + ot("creator") + br()
        xml += tab(2) + ot("creatorName") + creator_name.strip() + ct("creatorName") + br()
        creator_name_array = creator_name.split(",")
        xml += tab(2) + ot("givenName") + creator_name_array[1].strip() + ct("givenName") + br()
        xml += tab(2) + ot("familyName") + creator_name_array[0].strip() + ct("familyName") + br()
        if len(author_array) > 1:
            affiliation_array = author_array[1].split("|")
            for affiliation in affiliation_array:
                if len(affiliation.strip()) > 0:
                    xml += tab(2) + ot("affiliation") + affiliation.strip() + ct("affiliation") + br()
        xml += tab(1) + ct("creator") + br()
    xml += ct("creators") + br()
    return xml

def get_latest_commit_root_id(repo):
    commits = seafile_api.get_commit_list(repo.id, 0, 1)
    commit = commit_mgr.load_commit(repo.id, repo.version, commits[0].id)
    return commit.root_id

def get_latest_commit_id(repo):
    commits = seafile_api.get_commit_list(repo.id, 0, 1)
    return commits[0].id

def validate(doi_dict, repo_id, user_email):
    LOGGER.info("""Validate the DOI mandatory fields and content...""")

    doi_msg = []

    # 1. check mandatory fields
    # todo add more mandatory fields
    doi_headers_mandatory = ['Title', 'Author', 'Year', 'Description', 'Institute']
    s1 = set(doi_dict.keys())
    s2 = set(doi_headers_mandatory)

    mandatory_field_valid = s2.issubset(s1)
    if not mandatory_field_valid:
        invalid_fields = s2.difference(s1)
    else:
        invalid_fields = set()

    # 2. check content
    year_valid = validate_year(doi_dict.get('Year'))
    if not year_valid:
        invalid_fields.add('Year')
    author_valid = validate_author(doi_dict.get('Author'))
    if not author_valid:
        invalid_fields.add('Author')
    institute_valid = validate_institute(doi_dict.get('Institute'))
    if not institute_valid:
        invalid_fields.add('Institute')
    resource_type_valid = validate_resource_type(doi_dict.get("Resource Type"))
    if not resource_type_valid:
        invalid_fields.add('Resource Type')

    valid = mandatory_field_valid and year_valid and author_valid and institute_valid and resource_type_valid
    if not valid and user_email is not None:
        if len(invalid_fields) > 1:
            msg =  _('%(fields)s fields are either invalid or not filled.') % { 'fields': ', '.join(invalid_fields) }
        elif len(invalid_fields) == 1:
            msg =  _('%(field)s field is either invalid or not filled.') % { 'field': invalid_fields.pop() }
        doi_msg.append(msg)
        send_notification(doi_msg, repo_id, MSG_TYPE_INVALID_METADATA_MSG, user_email)
    return doi_msg

def validate_resource_type(txt):
    """resource_type checking, options:
    Libray, Project
    """
    valid = True
    if txt:
        pattern = re.compile("^(Library|Project)$", re.UNICODE)
        if not re.match(pattern, txt):
            valid = False
            msg = 'Wrong Institution string: ' + txt
            LOGGER.info(msg)
    else:
        valid = False
    return valid

def br():
    return "\n"

def tab(number):
    tabs = ""
    if number is not None and number > 0:
        for i in range (1, number+1):
            tabs += "\t"
    else:
        tabs = "\t"
    return tabs

def attrib(attrib, value):
    if value:
        if attrib:
            attrib += " "
        attrib += "=\"" + value + "\""
    return attrib

def ota(tag, attr):
    if attr:
        return "<" + tag + " " + attr + ">"
    else:
        return ot(tag)

def ot(tag):
    return "<" + tag + ">"

def ct(tag):
    return "</" + tag + ">"

def process_special_char(arg):
    return '%s' % (
        arg
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", "&apos;")
    )

def send_notification(msg, repo_id, notification_type, user_email, doi='', doi_link='', timestamp=''):
    # status: 'invalid', 'success', 'error'
    # TODO: replace 'doi_link' with 'doi' in production
    if notification_type == MSG_TYPE_KEEPER_DOI_SUC_MSG:
        c = {
            'to_user': user_email,
            'message_type': 'doi_suc_msg',
            'message': msg + doi,
            'timestamp': timestamp,
        }

        try:
            send_html_email(_('New notice on %s') % get_site_name(),
                                    'notifications/keeper_email.html', c,
                                    None, [user_email])

            LOGGER.info('Successfully sent email to %s' % user_email)
        except Exception as e:
            LOGGER.error('Failed to send email to %s, error detail: %s' % (user_email, e))

        UserNotification.objects._add_user_notification(user_email, notification_type,
            json.dumps({
                'message': (msg),
                'lib': repo_id,
                'archive_metadata': ARCHIVE_METADATA_TARGET,
                'doi': doi,
                'doi_link': doi_link,
        }))
    elif notification_type == MSG_TYPE_INVALID_METADATA_MSG:
        if isinstance(msg, list):
            UserNotification.objects._add_user_notification(user_email, notification_type,
                json.dumps({
                    'message': (' '.join(msg)),
                    'lib': repo_id,
                    'archive_metadata': ARCHIVE_METADATA_TARGET,
            }))
    elif notification_type == MSG_TYPE_KEEPER_DOI_MSG:
        UserNotification.objects._add_user_notification(user_email, notification_type,
            json.dumps({
                'message': (msg),
                'lib': repo_id,
                'archive_metadata': ARCHIVE_METADATA_TARGET,
                'doi': doi,
                'doi_link': doi_link,
        }))
    elif notification_type == MSG_TYPE_KEEPER_ARCHIVING_MSG:
        UserNotification.objects._add_user_notification(user_email, notification_type,
            json.dumps({
                'msg': (msg),   # unify format for backend  
                '_repo': repo_id,
                'status': 'prepare', # use 'prepare' to distinguish from backend sent notifications
        }))