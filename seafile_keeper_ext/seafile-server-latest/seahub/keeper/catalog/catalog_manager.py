# -*- coding: utf-8 -*-
#!/usr/bin/env python

import sys

import traceback

from seaserv import get_commits, get_commit, get_repo_owner, seafile_api
from seafobj import fs_mgr
from seahub.settings import ARCHIVE_METADATA_TARGET, KEEPER_MPG_IP_LIST_URL, SERVICE_URL

from keeper.cdc.cdc_manager import is_certified_by_repo_id
from keeper.common import parse_markdown, print_json

from keeper.utils import get_user_name

from keeper.models import Catalog, DoiRepo

import logging
import json
from netaddr import IPAddress, IPSet

import urllib.request, urllib.error, urllib.parse

from django.core.cache import cache
from django.db import connections

# time to live of the mpg IP set: day
IP_SET_TTL = 60 * 60 * 24

MAX_INT = 2147483647


def trim_by_len(str, max_len, suffix="..."):
    if str:
        str = str.strip()
        if str and len(str) > max_len:
            str = str[0:max_len] + suffix
        str = str(str, 'utf-8', errors='replace')
    return str


def reconnect_db():
    """
    Force reconnect db, a walkaround to fix (2006, 'MySQL server has gone away') issue,
    see https://code.djangoproject.com/ticket/21597#comment:29
    """
    connections['default'].close()
    connections['keeper'].close()


def get_mpg_ip_set():
    """
    Get MPG IP ranges from cache or from rena service if cache is expired
    """
    if cache.get('KEEPER_CATALOG_LAST_FETCHED') is None:
        logging.info("Put IPs to cache...")
        try:
            # get json from server
            response = urllib.request.urlopen(KEEPER_MPG_IP_LIST_URL)
            json_str = response.read()
            # parse json
            json_dict = json.loads(json_str)
            # get only ip ranges
            ip_ranges = [(list(ipr.items()))[0][0] for ipr in json_dict['details']]
            ip_set = IPSet(ip_ranges)
            cache.set('KEEPER_CATALOG_MPG_IP_SET', ip_set, None)
            cache.set(
                'KEEPER_CATALOG_LAST_FETCHED',
                json_dict['timestamp'],
                IP_SET_TTL)
        except Exception as e:
            logging.info("Cannot get/parse MPG IPs DB: %s", e)
            logging.info("Get IPs from old cache")
            ip_set = cache.get('KEEPER_CATALOG_MPG_IP_SET')
    else:
        logging.info("Get ips from cache...")
        ip_set = cache.get('KEEPER_CATALOG_MPG_IP_SET')
    return ip_set


def is_in_mpg_ip_range(ip):
    # only for tests!
    # return True
    return IPAddress(ip) in get_mpg_ip_set()


def generate_catalog_entry(repo):
    """
    Generate catalog entry in for the repo DB
    """
    reconnect_db()

    proj = {}

    try:
        proj["id"] = repo.id
        proj["name"] = repo.name
        email = get_repo_owner(repo.id)
        proj["owner"] = email
        user_name = get_user_name(email)
        if user_name != email:
            proj["owner_name"] = user_name
        proj["in_progress"] = True
        proj["modified"] = repo.last_modify

        commits = get_commits(repo.id, 0, 1)
        commit = get_commit(repo.id, repo.version, commits[0].id)
        dir = fs_mgr.load_seafdir(repo.id, repo.version, commit.root_id)
        file = dir.lookup(ARCHIVE_METADATA_TARGET)
        if file:
            md = file.get_content().decode('utf-8')
            md = parse_markdown(md)
            if md:
                # Author
                a = md.get("Author")
                if a:
                    a_list = a.split('\n')
                    authors = []
                    for _ in a_list:
                        author = {}
                        aa = _.split(';')
                        author['name'] = aa[0]
                        if len(aa) > 1 and aa[1].strip():
                            author['affs'] = [x.strip()
                                              for x in aa[1].split('|')]
                            author['affs'] = [x for x in author['affs'] if x]
                        authors.append(author)
                    if a:
                        proj["authors"] = authors

                # Description
                d = md.get("Description")
                if d:
                    proj["description"] = d

                # Comments
                c = md.get("Comments")
                if c:
                    proj["comments"] = c

                # Title
                t = md.get("Title")
                if t:
                    proj["title"] = t
                    del proj["in_progress"]

                # Year
                y = md.get("Year")
                if y:
                    proj["year"] = y

                # Institute
                i = md.get("Institute")
                if i:
                    proj["institute"] = i

                proj["is_certified"] = is_certified_by_repo_id(repo.id)

        # add or update project metadata in DB
        c = Catalog.objects.add_or_update_by_repo_id(repo.id, email, proj, repo.name)
        # Catalog_id
        proj["catalog_id"] = str(c.catalog_id)

    except Exception:
        msg = "repo_name: %s, id: %s" % (repo.name, repo.id)
        logging.error(msg)
        logging.error(traceback.format_exc())

    return proj


def generate_catalog_entry_by_repo_id(repo_id):
    """
    Generate catalog entry by repo_id
    """
    return generate_catalog_entry(seafile_api.get_repo(repo_id))


def get_catalog(filter='all'):
    """
    Get catalog metadata from pre-generated DB cache
    """
    reconnect_db()
    if filter == 'with_certificate':
        return add_landing_page_entry(Catalog.objects.get_certified())
    elif filter == 'with_metadata':
        return add_landing_page_entry(Catalog.objects.get_with_metadata())
    else:
        return add_landing_page_entry(Catalog.objects.get_all_mds_ordered())

def add_landing_page_entry(catalogs):

    for catalog in catalogs:
        repo_id = catalog.get('repo_id')
        if repo_id: 
            doi_repos = DoiRepo.objects.get_valid_doi_repos(repo_id)
            if doi_repos or catalog.get('is_archived'):
                url = SERVICE_URL + '/landing-page/libs/' + repo_id + '/'
                catalog['landing_page_url'] = url

    return catalogs


def delete_catalog_entry_by_repo_id(repo_id):
    """
    Delete catalog entry by repo_id
    """
    reconnect_db()
    Catalog.objects.delete_by_repo_id(repo_id)

def generate_catalog():
    """
    Generate entire catalog and put it into DB cache
    """
    repos_all = [r for r in seafile_api.get_repo_list(0, MAX_INT)
                 if get_repo_owner(r.id) != 'system']

    return [generate_catalog_entry(repo) for repo in
            sorted(repos_all, key=lambda x: x.last_modify, reverse=False)]

def clean_up_catalog():
    """
    Remove catalog entries for non existed repos
    """
    reconnect_db()
    repo_ids = [r.id for r in seafile_api.get_repo_list(0, MAX_INT)
                 if get_repo_owner(r.id) != 'system']

    i = 0
    for ce in Catalog.objects.get_all():
        if ce.repo_id not in repo_ids:
            ce.delete()
            i += 1
    return i


def usage():
    print('Usage: catalog_manager.py (sync-db|gen-db)')

if __name__ == "__main__":

    try:
        param = sys.argv[1]
    except:
        usage()
        sys.exit(1)

    if param == 'clean-db':
        print(('%s catalog entries have been cleaned up' % clean_up_catalog()))
    elif param == 'gen-db':
        print(('Catalog has been sucessfully [re]generated, number of processed entries:', len(generate_catalog())))
    else:
        print((str(sys.argv)))
        usage()
        sys.exit(1)
