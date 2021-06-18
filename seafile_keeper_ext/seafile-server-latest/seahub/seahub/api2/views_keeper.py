from thirdpart.rest_framework.views import APIView
from thirdpart.rest_framework import status
from thirdpart.rest_framework.response import Response

from seahub.settings import DEBUG, DOI_SERVER, DOI_USER, DOI_PASSWORD, DOI_TIMEOUT, \
    SERVICE_URL, SERVER_EMAIL, ARCHIVE_METADATA_TARGET, BLOXBERG_CERTS_STORAGE, BLOXBERG_CERTS_LIMIT
from seahub.base.templatetags.seahub_tags import email2contact_email
from seahub.auth.decorators import login_required
from django.utils.decorators import method_decorator
from seahub.api2.utils import api_error, json_response
from seahub.views import check_folder_permission
from seahub.utils import render_error
from seahub.utils.repo import is_repo_owner
from seahub.options.models import UserOptions, CryptoOptionNotSetError
from seaserv import seafile_api

from keeper.catalog.catalog_manager import get_catalog, add_landing_page_entry
from keeper.bloxberg.bloxberg_manager import generate_certify_payload, \
    get_file_by_path, hash_file, hash_library, create_bloxberg_certificate, \
    get_md_json, decode_metadata, request_create_bloxberg_certificate, \
    generate_bloxberg_certificate_pdf, get_latest_snapshot_certificate, \
    send_start_snapshot_notification, send_failed_notice, \
    update_snapshot_certificate, get_commit_id
from keeper.doi.doi_manager import get_metadata, generate_metadata_xml, \
    get_latest_commit_id, send_notification, \
    MSG_TYPE_KEEPER_DOI_MSG, MSG_TYPE_KEEPER_DOI_SUC_MSG
from keeper.models import CDC, DoiRepo, Catalog, BCertificate

from django.http import JsonResponse, HttpResponse, Http404, StreamingHttpResponse
from django.shortcuts import render

from django.utils.translation import ugettext as _, activate, get_language
from django.core.urlresolvers import reverse

from urllib.parse import quote_plus

import logging
import json
import datetime
import requests
import os
import traceback
from requests.exceptions import ConnectionError, Timeout

from keeper.utils import add_keeper_archiving_task, query_keeper_archiving_status, check_keeper_repo_archiving_status,\
    archive_metadata_form_validation, get_mpg_ips_and_institutes, get_archive_metadata, save_archive_metadata, \
    is_in_mpg_ip_range, MPI_NAME_LIST_DEFAULT

from keeper.common import parse_markdown_doi
from seafevents.keeper_archiving.db_oper import DBOper, MSG_TYPE_KEEPER_ARCHIVING_MSG
from seafevents.keeper_archiving.task_manager import MSG_DB_ERROR, MSG_ADD_TASK, MSG_WRONG_OWNER, MSG_MAX_NUMBER_ARCHIVES_REACHED, MSG_CANNOT_GET_QUOTA, MSG_LIBRARY_TOO_BIG, MSG_EXTRACT_REPO, MSG_ADD_MD, MSG_CREATE_TAR, MSG_PUSH_TO_HPSS, MSG_ARCHIVED, MSG_CANNOT_FIND_ARCHIVE, MSG_SNAPSHOT_ALREADY_ARCHIVED
import seaserv

from base64 import b64decode
from pickle import loads

logger = logging.getLogger(__name__)

DOXI_URL = DOI_SERVER + "/doxi/rest/doi"
allowed_ip_prefixes = []
# allowed_ip_prefixes = ['','172.16.1','10.10.','192.168.1.10','192.129.1.102']

def is_password_set(repo_id, username):
    return seafile_api.is_password_set(repo_id, username)

def get_next_url_from_request(request):
    return request.GET.get('next', None)

def get_commit(repo_id, repo_version, commit_id):
    return seaserv.get_commit(repo_id, repo_version, commit_id)

# @login_required
def project_catalog_starter(request):
    """
    Get project catalog, first call
    """
    return render(request, 'project_catalog_react.html', {
        'current_page': 1,
        'per_page': 25,
    })


class CatalogView(APIView):
    """
    Returns Keeper Catalog.
    """
    @json_response
    def get(self):
        catalog = get_catalog()
        return catalog


class CatalogReactView(APIView):
    """
    Returns Keeper Catalog.
    """
    @json_response
    def post(self, request):

        # check access
        can_access = DEBUG
        if not can_access:
            remote_addr = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR'))
            # HTTP_X_FORWARDED_FOR now contains full proxy chain: if 2 IPs here, take first one!! (client)
            if remote_addr:
                s = [ip.strip() for ip in remote_addr.split(",")]
                remote_addr = s.pop(0)
                if remote_addr:
                    for allowed_ip_prefix in allowed_ip_prefixes:
                        if remote_addr.startswith(allowed_ip_prefix):
                            can_access = True
                            break
                    if not can_access and is_in_mpg_ip_range(remote_addr):
                        can_access = True

        if not can_access:
            return {"is_access_denied": True}

        facets = {}
        try:
            page = int(request.data.get('page', '1'))
            per_page = int(request.data.get('per_page', '25'))
            search_term = request.data.get('search_term', None)
            scope = request.data.get('scope', None)
            facets.update(
                author=request.data.get('author_facet', None),
                year=request.data.get('year_facet', None),
                institute=request.data.get('institute_facet', None),
                director=request.data.get('director_facet', None),
            )
        except ValueError:
            page = 1
            per_page = 25

        if page <= 0:
            error_msg = 'page invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        if per_page <= 0:
            error_msg = 'per_page invalid.'
            return api_error(status.HTTP_400_BAD_REQUEST, error_msg)

        if not(scope and len(scope) > 0):
            scope = None;

        start = (page - 1) * per_page

        # set limit to per_page + 1 to eval has_more value
        limit = per_page + 1

        try:
            catalog = Catalog.objects.get_mds_react(search_term=search_term, scope=scope, facets=facets, start=start, limit=limit)
        except Exception as e:
            import traceback
            logger.error(traceback.format_exc())
            logger.error(e)
            error_msg = 'Internal Server Error'
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR, error_msg)

        has_more = len(catalog.get("items")) == per_page + 1

        return {"more": has_more, "items": catalog.get("items")[:per_page], "scope": catalog.get("scope"), "facets": catalog.get("facets")}


class CanCertify(APIView):
    """
    Certify Preprocessing
    """
    def post(self, request, format=None):
        repo_id = request.data['repo_id']
        content_type = request.data['type']
        path = request.data['path']
        user_email = request.user.username

        repo_owner = get_repo_owner(repo_id)
        if repo_owner != user_email:
            return api_error(status.HTTP_400_BAD_REQUEST, _('Permission denied'))

        repo = get_repo(repo_id)
        if content_type == 'dir' and repo.file_count > int(BLOXBERG_CERTS_LIMIT):
            return api_error(status.HTTP_400_BAD_REQUEST, _('The library contains too many files for the certification. The current limit is %(limit)s files per library.') % { 'limit':  BLOXBERG_CERTS_LIMIT})

        snapshot_cert = get_latest_snapshot_certificate(repo_id, path)
        if snapshot_cert is None or snapshot_cert.status == "FAILED":
            return JsonResponse({
                'status': 'success'
            })
        elif snapshot_cert.status == "DONE":
            if content_type == 'dir':
                return api_error(status.HTTP_400_BAD_REQUEST, _('This version of the library has already been successfully certified.'))
            elif content_type == 'file':
                return api_error(status.HTTP_400_BAD_REQUEST, _('This version of the file has already been successfully certified.'))
        elif snapshot_cert.status == "IN_PROGRESS":
            if snapshot_cert.created + datetime.timedelta(seconds=3600) < datetime.datetime.now():# lazy update certificate status
                snapshot_cert.status = "FAILED"
                snapshot_cert.error_msg = "timeout(lazy update)"
                snapshot_cert.save()
                return JsonResponse({
                    'status': 'success'
                })
            return api_error(status.HTTP_400_BAD_REQUEST, _('Certification is already in progress.'))

        return api_error(status.HTTP_400_BAD_REQUEST, _('The certification has failed, please try again in a few minutes. In case it keeps failing, please contact the Keeper Support.'))

class BloxbergView(APIView):
    """
    Certify a single file or a Library
    """

    def post(self, request, format=None):
        repo_id = request.data['repo_id']
        path = request.data['path']
        content_name = request.data['name']
        content_type = request.data['type']
        user_email = request.user.username
        checksumArr = []
        language_code = get_language()

        catalog = Catalog.objects.get_by_repo_id(repo_id)
        if catalog is None:
            return api_error(status.HTTP_400_BAD_REQUEST, _('Permission denied'))
        catalog_md = catalog.md

        repo_owner = get_repo_owner(repo_id)
        if repo_owner != user_email:
            return api_error(status.HTTP_400_BAD_REQUEST, _('Permission denied'))

        commit_id = get_commit_id(repo_id)
        if content_type == 'dir':
            obj_id = create_bloxberg_certificate(repo_id, path, 0, content_type, content_name, datetime.datetime.now(), '', user_email, json.dumps(catalog_md), {}, "IN_PROGRESS")
            logger.info(f'{obj_id} IN_PROGESS')
            file_map = hash_library(repo_id, user_email)
            for dPath, dHash in file_map.items():
                checksumArr.append(dHash)

            send_start_snapshot_notification(repo_id, datetime.datetime.now(), user_email)
            try:
                response_bloxberg = request_create_bloxberg_certificate(generate_certify_payload(user_email, catalog_md, checksumArr))
                if response_bloxberg is not None and response_bloxberg.status_code == 200:
                    certificates = response_bloxberg.json()
                    transaction_id = decode_metadata(certificates)
                    logger.info(f'Transaction successful! {obj_id}')
                    update_snapshot_certificate(obj_id, certificates=json.dumps(certificates), transaction_id = transaction_id)
                    for dPath, dHash in file_map.items():
                        created_time = datetime.datetime.now()
                        create_bloxberg_certificate(repo_id, dPath, transaction_id, 'child', os.path.basename(dPath), created_time, dHash, user_email, json.dumps(catalog_md), '', "IN_PROGRESS")
                    generate_bloxberg_certificate_pdf(certificates, transaction_id, repo_id, obj_id, user_email, content_type, path, language_code)
                    return JsonResponse(response_bloxberg.json(), safe=False)
                else:
                    logger.info(f'Transaction failed. {obj_id}')
                    update_snapshot_certificate(obj_id, status="FAILED", error_msg="transaction failed")
                    send_failed_notice(repo_id, '', datetime.datetime.now(), user_email)
                    if response_bloxberg is not None:
                        logger.info(response_bloxberg.json())

            except Exception as e:
                logger.error(traceback.format_exc())
                if transaction_id is None:
                    transaction_id = 0
                update_snapshot_certificate(obj_id, status="FAILED", error_msg = str(e), transaction_id = transaction_id)
                send_failed_notice(repo_id, transaction_id, datetime.datetime.now(), user_email)

        elif content_type == 'file':
            obj_id = create_bloxberg_certificate(repo_id, path, 0, content_type, content_name, datetime.datetime.now(), '', user_email, json.dumps(catalog_md), {}, "IN_PROGRESS")
            logger.info(f'{obj_id} IN_PROGESS')
            file = get_file_by_path(repo_id, path)
            checksum = hash_file(file)
            checksumArr.append(checksum)

            try:
                response_bloxberg = request_create_bloxberg_certificate(generate_certify_payload(user_email, catalog_md, checksumArr))
                if response_bloxberg is not None and response_bloxberg.status_code == 200:
                    logger.info(f'Transaction successful! {obj_id}')
                    certificates = response_bloxberg.json()
                    transaction_id = decode_metadata(certificates)
                    created_time = datetime.datetime.now()
                    update_snapshot_certificate(obj_id, certificates=json.dumps(certificates[0]), transaction_id=transaction_id, checksum=checksum)
                    generate_bloxberg_certificate_pdf(certificates, transaction_id, repo_id, obj_id, user_email, content_type, path, language_code)
                    return JsonResponse(certificates, safe=False)
                else:
                    logger.info(f'Transaction failed. {obj_id}')
                    error_msg = response_bloxberg.text if response_bloxberg is not None else "Generate pdf request failed, response is None."
                    logger.error(error_msg)
            except Exception as e:
                logger.error(traceback.format_exc())
                update_snapshot_certificate(obj_id, status = "FAILED", error_msg = str(e))

        return api_error(status.HTTP_400_BAD_REQUEST, _('The certification has failed, please try again in a few minutes. In case it keeps failing, please contact the Keeper Support.'))

def request_doxi(shared_link, doxi_payload):
    try:
        # credentials for https://test.doi.mpdl.mpg.de/
        user=DOI_USER
        pwd=DOI_PASSWORD
        headers = {'Content-Type': 'text/xml'}
        response = requests.put(DOXI_URL, auth=(user, pwd), headers=headers, params={'url': shared_link}, data=doxi_payload, timeout=DOI_TIMEOUT)
        return response
    except Timeout:
        return JsonResponse({
            'msg': 'DOXI request timeout',
            'status': 'error',
            }, status=408)
    except ConnectionError as e:
        logger.error(str(e))

def get_landing_page_url(repo_id, commit_id):
    return "{}/doi/libs/{}/{}".format(SERVICE_URL, repo_id, commit_id)

class AddDoiView(APIView):
    """
    Create DOI
    """
    def post(self, request, format=None):
        repo_id = request.data['repo_id']
        user_email = request.user.username
        repo = get_repo(repo_id)
        doi_repos = DoiRepo.objects.get_valid_doi_repos(repo_id)
        if doi_repos:
            msg = 'This library already has a DOI. '
            url_landing_page = get_landing_page_url(doi_repos[0].repo_id, doi_repos[0].commit_id)
            send_notification(msg, repo_id, MSG_TYPE_KEEPER_DOI_MSG, user_email, doi_repos[0].doi, url_landing_page)
            return api_error(status.HTTP_400_BAD_REQUEST, msg + doi_repos[0].doi)

        metadata = get_metadata(repo_id, user_email, "assign DOI")

        if 'error' in metadata:
            return api_error(status.HTTP_400_BAD_REQUEST, metadata.get('error'))

        metadata_xml = generate_metadata_xml(metadata)
        commit_id = get_latest_commit_id(repo)

        url_landing_page = get_landing_page_url(repo_id, commit_id)
        response_doxi = request_doxi(url_landing_page, metadata_xml)

        if response_doxi is not None:
            if response_doxi.status_code == 201:
                doi = 'https://doi.org/' + response_doxi.text
                logger.info(doi)
                repo_owner = get_repo_owner(repo_id)
                DoiRepo.objects.add_doi_repo(repo_id, repo.name, doi, None, commit_id, repo_owner, metadata)
                msg = _('DOI successfully created') + ': '
                doi_repos = DoiRepo.objects.get_doi_by_commit_id(repo_id, commit_id)
                send_notification(msg, repo_id, MSG_TYPE_KEEPER_DOI_SUC_MSG, user_email, doi, url_landing_page, timestamp=doi_repos[0].created)
                return JsonResponse({
                    'msg': msg + doi,
                    'status': 'success',
                    })
            elif response_doxi.status_code == 408:
                msg = 'The assign DOI functionality is currently unavailable. Please try again later. If the problem persists, please contact Keeper support.'
                send_notification(msg, repo_id, MSG_TYPE_KEEPER_DOI_MSG, user_email)
                return api_error(status.HTTP_400_BAD_REQUEST, msg)
            else:
                logger.info(response_doxi.status_code)
                logger.info(response_doxi.text)
                msg = 'Failed to create DOI. Please try again later. If the problem persists, please contact Keeper support.'
                send_notification(msg, repo_id, MSG_TYPE_KEEPER_DOI_MSG, user_email)
                return api_error(status.HTTP_400_BAD_REQUEST, msg)
        else:
            msg = 'The assign DOI functionality is currently unavailable. Please try again later. If the problem persists, please contact Keeper support.'
            send_notification(msg, repo_id, MSG_TYPE_KEEPER_DOI_MSG, user_email)
            return api_error(status.HTTP_400_BAD_REQUEST, msg)


def _try_decode_md(md):
    #fix pickle object if not converted to dict
    if md is not None and isinstance(md, str):
        try:
            md = md.encode()
            md = b64decode(md)
            md = loads(md, encoding="UTF8")
        except Exception as e:
            logger.error(f'Cannot parse md: {str(e)}, set md = {{}}')
            return None 

    return md

def DoiView(request, repo_id, commit_id):
    doi_repos = DoiRepo.objects.get_doi_by_commit_id(repo_id, commit_id)
    repo_owner = get_repo_owner(repo_id)

    if len(doi_repos) == 0:
        return render(request, '404.html')

    doi_repo = doi_repos[0]

    md = _try_decode_md(doi_repo.md)
    if md is None:
        return render(request, '404.html')

    if doi_repo.rm is not None:
        return render(request, './catalog_detail/tombstone_page.html', {
            'doi': doi_repo.doi,
            'md_dict': md,
            'authors': '; '.join(get_authors_from_md(md)),
            'institute': md.get("Institute").replace(";", "; "),
            'library_name': doi_repo.repo_name,
            'owner_contact_email': email2contact_email(repo_owner) })

    cdc = get_cdc_id_by_repo(repo_id) is not None
    link = SERVICE_URL + "/repo/history/view/" + repo_id + "/?commit_id=" + commit_id
    return render(request, './catalog_detail/landing_page.html', {
        'share_link': link,
        'cdc': cdc,
        'authors': '; '.join(get_authors_from_md(md)),
        'institute': md.get("Institute").replace(";", "; "),
        'commit_id': commit_id,
        'doi_dict': md,
        'doi': doi_repo.doi,
        'owner_contact_email': email2contact_email(repo_owner) })


def get_authors_from_md(md):
    authors = md.get("Author").split('\n')
    result_author = []
    for author in authors:
        author_array = author.split(";")
        author_name = author_array[0].strip()
        name_array = author_name.split(",")
        tmpauthor = ''
        for i in range(len(name_array)):
            if ( i <= 0 and len(name_array[i].strip()) > 1 ):
                tmpauthor += name_array[i]+", "
            elif (len(name_array[i].strip()) >= 1):
                tmpauthor += name_array[i].strip()[:1] + "."

        if len(author_array) > 1 and len(author_array[1].strip()) > 0:
            affiliations = author_array[1].split("|")
            tmpauthor += " (" + ", ".join(map(str.strip, affiliations)) + ")"

        result_author.append(tmpauthor)
    return result_author

def get_repo(repo_id):
    return seafile_api.get_repo(repo_id)

def get_repo_owner(repo_id):
    return seafile_api.get_repo_owner(repo_id)

def get_cdc_id_by_repo(repo_id):
    """Get cdc_id by repo_id. Return None if nothing found"""
    return CDC.objects.get_cdc_id_by_repo(repo_id)


@login_required
def LandingPageView(request, repo_id):
    catalog = Catalog.objects.get_by_repo_id(repo_id)
    md = catalog.md
    repo_owner = catalog.owner

    archives = []
    archive_repos = DBOper().get_archives(repo_id=repo_id)
    if archive_repos is not None and len(archive_repos) > 0:
        for archive_repo in archive_repos:
            archive = {
                'version': archive_repo.version,
                'created': archive_repo.created.strftime('%Y-%m-%d %H:%M:%S'),
                'repo_id': archive_repo.repo_id
            }
            archives.append(archive)
        archives.reverse()

    doi_repos = []
    qs_doi_repos = DoiRepo.objects.get_doi_repos_by_repo_id(repo_id)
    if qs_doi_repos is not None:
        for doi_repo in qs_doi_repos:
            doi = {
                'created': doi_repo.created.strftime('%Y-%m-%d %H:%M:%S'),
                'doi': doi_repo.doi
            }
            doi_repos.append(doi)

    bloxberg_certs = []
    qs_bloxberg_certs = BCertificate.objects.get_finished_bloxberg_certificates(repo_owner, repo_id)
    if qs_bloxberg_certs is not None:
        for bloxberg_cert in qs_bloxberg_certs:
            cert = {
                'content_name': bloxberg_cert.content_name,
                'created': bloxberg_cert.created.strftime('%Y-%m-%d %H:%M:%S'),
                'path': bloxberg_cert.path,
                'transaction_id': bloxberg_cert.transaction_id,
                'checksum': bloxberg_cert.checksum
            }
            bloxberg_certs.append(cert)

    return render(request, './catalog_detail/lib_detail_react.html', {
        'repo_name': md.get('title') if md and md.get('title') else catalog.repo_name,
        'repo_desc': md.get('description') if md and md.get('description') else '',
        'institute': md.get('Institute') if md and md.get('Institute') else '',
        'authors': get_authors_from_catalog_md(md) if md and md.get('authors') else repo_owner,
        'year': md.get('year') if md and md.get('year') else '',

        'doi_repos': json.dumps(doi_repos),
        'archive_repos': json.dumps(archives),
        'bloxberg_certs': json.dumps(bloxberg_certs),
        'hasCDC': get_cdc_id_by_repo(repo_id) is not None,
        'owner_contact_email':  SERVER_EMAIL if repo_owner is None else email2contact_email(repo_owner)
    })

def get_authors_from_catalog_md(md):
    result_authors = []
    for author in md.get("authors"):
        name_array = author.get("name").split(",")
        tmp = name_array[0].strip()
        if name_array[1]:
            tmp += ', ' + name_array[1].strip()[:1] + '.'
        affs = author.get("affs")
        if affs:
            tmp += " (" + ", ".join(map(str.strip, affs)) + ")"
        result_authors.append(tmp)

    return "; ".join(result_authors)


def ArchiveView(request, repo_id, version_id, is_tombstone):
    archive_repos = DBOper().get_archives(repo_id=repo_id, version = version_id)
    if archive_repos is None or len(archive_repos) == 0:
        return render(request, '404.html')

    archive_repo = archive_repos[0]
    repo_owner = get_repo_owner(repo_id)
    archive_md = parse_markdown_doi(archive_repo.md)
    commit_id = archive_repo.commit_id
    cdc = False if get_cdc_id_by_repo(repo_id) is None else True

    if repo_owner is None:
        if is_tombstone == '1':
            return render(request, './catalog_detail/tombstone_page.html', {
                    'md_dict': archive_md,
                    'authors': '; '.join(get_authors_from_md(archive_md)),
                    'institute': archive_md.get("Institute").replace(";", "; "),
                    'library_name': archive_repo.repo_name,
                    'owner_contact_email': email2contact_email(repo_owner) })

        repo_owner_email = SERVER_EMAIL
        link = SERVICE_URL + '/archive/libs/' + repo_id + '/' + version_id + '/1/'
    else:
        repo_owner_email = email2contact_email(repo_owner)
        link = SERVICE_URL + "/repo/history/view/" + repo_id + "/?commit_id=" + commit_id

    return render(request, './catalog_detail/archive_page.html', {
        'share_link': link,
        'authors': '; '.join(get_authors_from_md(archive_md)),
        'institute': archive_md.get("Institute").replace(";", "; "),
        'commit_id': commit_id,
        'md_dict': archive_md,
        'cdc': cdc,
        'owner_contact_email': email2contact_email(repo_owner) })


class CanArchive(APIView):

    """Quota checking before adding archiving"""

    def get(self, request):
        repo_id = request.GET.get('repo_id', None)
        version = request.GET.get('version', None)
        owner = request.user.username
        resp = query_keeper_archiving_status(repo_id, owner, version)
        # logger.info("RESP:{}".format(resp))
        return JsonResponse(resp)


    def post(self, request):

        repo_id = request.data.get('repo_id', None)
        owner = request.data.get('owner', request.user.username)
        version = request.data.get('version', None)
        language_code = request.data.get('language_code', None)
        if language_code == 'de':
            activate(language_code)

        # library is already in the task query
        resp_query = query_keeper_archiving_status(repo_id, owner, version)
        logger.debug('check QUEUED or PROCESSING: %s', resp_query)
        if resp_query.get('status') in ('QUEUED', 'PROCESSING'):
            msg = _('This library is currently being archived.')
            return JsonResponse({
                'msg': msg,
                'status': 'in_processing'
            })
        elif resp_query.get('status') == 'ERROR':
            return JsonResponse({
                'msg': resp_query.get('msg') or 'system_error',
                'status': 'system_error'
            })

        resp_is_archived = check_keeper_repo_archiving_status(repo_id, owner, 'is_snapshot_archived')
        logger.debug('is_snapshot_archived: %s', resp_is_archived)
        if resp_is_archived.get('is_snapshot_archived') == 'true':
            return JsonResponse({
                'status': 'snapshot_archived'
            })

        resp_quota = check_keeper_repo_archiving_status(repo_id, owner, 'get_quota')
        logger.debug('get_quota: %s', resp_quota)
        if 'remains' in resp_quota and resp_quota.get('remains') <= 0:
            return JsonResponse({
                'status': 'quota_expired'
            })

        resp_is_repo_too_big = check_keeper_repo_archiving_status(repo_id, owner, 'is_repo_too_big')
        logger.debug('is_repo_too_big: %s', resp_is_repo_too_big)
        if resp_is_repo_too_big.get('is_repo_too_big') == 'true':
            return JsonResponse({
                'status': 'is_too_big'
            })

        metadata = get_metadata(repo_id, owner, 'archive library')
        logger.debug('get metadata archive library: %s', metadata)
        if 'error' in metadata:
            resp = {
                'msg': metadata.get('error'),
                'status': 'metadata_error',
            }
            q = resp_quota.get("remains")
            q and resp.update(quota=q)
            return JsonResponse(resp)

        return JsonResponse({
            'quota': resp_quota.get('remains'),
            'status': 'success'
        })


class ArchiveLib(APIView):

    """ create keeper archive for a library """

    def get(self, request):
        repo_id = request.GET.get('repo_id', None)
        user_email = request.user.username
        resp = add_keeper_archiving_task(repo_id, user_email)
        # logger.info("RESP:{}".format(vars(resp)))
        return JsonResponse(resp)

    def post(self, request):

        # repo_id = request.POST.get('repo_id', None)
        # owner = request.POST.get('owner', None)
        # language_code = request.POST.get('language_code', None)
        repo_id = request.data.get('repo_id', None)
        owner = request.data.get('owner', request.user.username)
        language_code = request.data.get('language_code', None)
        if language_code == 'de':
            activate(language_code)


        # add new archiving task
        resp_archive = add_keeper_archiving_task(repo_id, owner)
        logger.debug('resp_archive: %s', resp_archive)
        if resp_archive.get('status') == 'ERROR':
            return JsonResponse({
                'msg': _(resp_archive.get('msg')),
                'status': 'error'
            })
        return JsonResponse({
                'msg':  _(resp_archive.get('msg')),
                'status': 'success'
            })

class ArchiveMetadata(APIView):
    """docstring for ArchiveMetadata"""

    def get(self, request):
        repo_id = request.GET.get('repo_id')
        if not(repo_id):
            return api_error(status.HTTP_400_BAD_REQUEST, 'Bad request.')

        amd = get_archive_metadata(repo_id)
        if not(amd):
            return api_error(status.HTTP_500_INTERNAL_SERVER_ERROR , 'Cannot get ' + ARCHIVE_METADATA_TARGET)

        errors = archive_metadata_form_validation(amd)
        if errors:
            amd.update(errors=errors)

        return JsonResponse(amd)

    def post(self, request):
        data = request.data

        repo_id = data.get('repo_id')
        if not(repo_id):
            return api_error(status.HTTP_400_BAD_REQUEST, 'Bad request.')

        if data.get('validate'):
            errors = archive_metadata_form_validation(data)
            if errors:
                data.update(errors=errors)

        save_archive_metadata(repo_id, data)

        data.update(redirect_to='%s/library/%s/%s/' % (SERVICE_URL, repo_id, quote_plus(get_repo(repo_id).name)))

        return JsonResponse(data)


class MPGInstitutes(APIView):
    """ get MPI Name list from RENA """

    def get(self, request):
        _, ins_list = get_mpg_ips_and_institutes()
        ins_list = ins_list or MPI_NAME_LIST_DEFAULT
        return JsonResponse(ins_list, safe=False)


class LibraryDetailsView(APIView):
    """ list LibraryDetails for sidenav """

    def get(self, request):
        return JsonResponse([
            {"repo_id": e.repo_id, "repo_name": e.repo_name}
            for e in Catalog.objects.get_library_details_entries(request.user.username)
         ], safe=False)

@login_required
def BloxbergCertView(request, transaction_id, checksum=''):
    """ View bloxberg certificate(s) """
    certificate = BCertificate.objects.get_presentable_certificate(transaction_id, checksum)
    repo_id = certificate.repo_id
    repo = get_repo(repo_id)
    if not repo:
        raise Http404

    username = request.user.username
    repo_owner = get_repo_owner(repo_id)
    if repo_owner != username:
        return render_error(request, _('Permission denied'))

    try:
        server_crypto = UserOptions.objects.is_server_crypto(username)
    except CryptoOptionNotSetError:
        # Assume server_crypto is ``False`` if this option is not set.
        server_crypto = False

    reverse_url = reverse('lib_view', args=[repo_id, repo.name, ''])
    if repo.encrypted and \
        (repo.enc_version == 1 or (repo.enc_version == 2 and server_crypto)) \
        and not is_password_set(repo.id, username):
        return render(request, 'decrypt_repo_form.html', {
                'repo': repo,
                'next': get_next_url_from_request(request) or reverse_url,
                })

    if certificate.content_type == 'dir':
        commit_id = certificate.commit_id

        current_commit = get_commit(repo.id, repo.version, commit_id)
        if not current_commit:
            current_commit = get_commit(repo.id, repo.version, repo.head_cmmt_id)

        certificates = BCertificate.objects.get_children_bloxberg_certificates(transaction_id, repo_id)
        checksum_map = {}
        for certificate in certificates:
            checksum_map[str(certificate.path)] = certificate.checksum

        return render(request, 'bloxberg_repo_snapshot_react.html', {
                'repo': repo,
                'current_commit': current_commit,
                'transaction_id': transaction_id,
                'checksums': json.dumps(checksum_map),
                })

    else:
        md_json = json.loads(certificate.md)
        pdf_url = SERVICE_URL + "/api2/bloxberg-pdf/"+ transaction_id + "/" + checksum + "/?p=" + quote_plus(certificate.path)
        metadata_url = SERVICE_URL + "/api2/bloxberg-metadata/"+ transaction_id + "/" + checksum + "/?p=" + quote_plus(certificate.path)
        history_file_url = ""
        all_file_revisions = seafile_api.get_file_revisions(repo_id, certificate.commit_id, certificate.path, 50)
        if all_file_revisions is not None:
            history_file_url =  "/repo/" + repo_id + "/" + all_file_revisions[0].rev_file_id + "/download/?file_name=" + quote_plus(certificate.content_name) + "&p=" + quote_plus(certificate.path)
        else:
            logger.error(f'commit_id: {certificate.commit_id}')
            logger.error(f'path: {certificate.path}')
        if md_json.get('authors'):
            authors = get_authors_from_catalog_md(md_json)
            return render(request, './catalog_detail/bloxberg_cert_page.html', {
                'repo_name': md_json.get('title'),
                'repo_desc': md_json.get('description') if md_json.get('description') else '',
                'institute': md_json.get('institute') if md_json.get('Institute') else '',
                'authors': authors,
                'year': md_json.get('year'),
                'transaction_id': certificate.transaction_id,
                'pdf_url': pdf_url,
                'metadata_url': metadata_url,
                'history_file_url': history_file_url
            })
        elif md_json.get('Title'): #backwards compatible(certificates created before 2.0)
            return render(request, './catalog_detail/bloxberg_cert_page.html', {
                'repo_name': md_json.get('Title'),
                'repo_desc': md_json.get('Description') if md_json.get('Description') else '',
                'institute': md_json.get('Institute') if md_json.get('Institute') else '',
                'authors': md_json.get('Author'),
                'year': md_json.get('Year'),
                'transaction_id': certificate.transaction_id,
                'pdf_url': pdf_url,
                'metadata_url': metadata_url,
                'history_file_url': history_file_url
            })
        else:
            return render(request, './catalog_detail/bloxberg_cert_page.html', {
                'repo_name': md_json.get('name'),
                'repo_desc': md_json.get('Description') if md_json.get('Description') else '',
                'institute': md_json.get('Institute') if md_json.get('Institute') else '',
                'authors': md_json.get('owner'),
                'year': '',
                'transaction_id': certificate.transaction_id,
                'pdf_url': pdf_url,
                'metadata_url': metadata_url,
                'history_file_url': history_file_url
            })

class BloxbergPdfView(APIView):
    @method_decorator(login_required)
    def get(self, request, transaction_id, checksum, format=None):
        username = request.user.username
        path = request.GET.get('p', '')
        try:
            certificate = BCertificate.objects.get_bloxberg_certificate(transaction_id, checksum, path)
            if not certificate:
                return Http404('not found')
            repo_owner = get_repo_owner(certificate.repo_id)
            if repo_owner != username:
                return render_error(request, _('Permission denied'))
            pdf_url = BLOXBERG_CERTS_STORAGE + '/' + certificate.owner + '/' + transaction_id + '/' + certificate.pdf
            response = StreamingHttpResponse(open(pdf_url, 'rb'))
            response['Content-Disposition'] = 'inline;filename=' + pdf_url
            return response
        except FileNotFoundError:
            raise Http404('not found')

class BloxbergMetadataJsonView(APIView):
    @method_decorator(login_required)
    def get(self, request, transaction_id, checksum, format=None):
        username = request.user.username
        try:
            certificate = BCertificate.objects.get_presentable_certificate(transaction_id, checksum)
            if not certificate:
                return Http404('not found')
            repo_owner = get_repo_owner(certificate.repo_id)
            if repo_owner != username:
                return render_error(request, _('Permission denied'))
            if "@context" in certificate.md_json:
                response = HttpResponse(certificate.md_json, content_type='application/text charset=utf-8')
            else:
                response = HttpResponse(certificate.md_json.replace("context","@context", 1), content_type='application/text charset=utf-8')
            response['Content-Disposition'] = 'attachment; filename="metadata.json"'
            return response
        except FileNotFoundError:
            raise Http404('not found')
