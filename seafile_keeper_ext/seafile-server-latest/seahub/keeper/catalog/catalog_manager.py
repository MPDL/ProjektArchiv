#!/usr/bin/env python

import traceback

from seaserv import get_commits, get_commit, get_repo_owner, seafile_api
from seafobj import fs_mgr
from seahub.settings import ARCHIVE_METADATA_TARGET

from keeper.cdc.cdc_manager import is_certified_by_repo_id, parse_markdown, get_user_name

import logging
import json
from netaddr import IPAddress, IPSet

import urllib2

from django.core.cache import cache

#time to live of the mpg IP set: day
IP_SET_TTL = 60 * 60 * 24

DEBUG = False

MAX_INT = 2147483647

JSON_DATA_URL = 'https://rena.mpdl.mpg.de/iplists/keeper.json'

def trim_by_len(str, max_len, suffix="..."):
    if str:
        str = str.strip()
        if str and len(str) > max_len:
            str = str[0:max_len] + suffix
        str = unicode(str, "utf-8")
    return str

def strip_uni(str):
    if str:
        str = unicode(str.strip(), "utf-8")
    return str

def get_mpg_ip_set():
    """Get MPG IP ranges from cache or from rena service if cache is expired"""
    if cache.get('KEEPER_CATALOG_LAST_FETCHED') is None:
        logging.info("Put ips to cache...")
        try:
            # get json from server
            response = urllib2.urlopen(JSON_DATA_URL)
            json_str = response.read()
            # parse json
            json_dict = json.loads(json_str)
            # get only ip ranges
            ip_ranges = [(ipr.items())[0][0] for ipr in json_dict['details']]
            ip_set = IPSet(ip_ranges)
            cache.set('KEEPER_CATALOG_MPG_IP_SET', ip_set, None)
            cache.set('KEEPER_CATALOG_LAST_FETCHED', json_dict['timestamp'], IP_SET_TTL)
        except Exception as e:
            logging.info("Cannot get/parse MPG IPs DB: " + ": ".join(str(i) for i in e))
            logging.info("Get IPS from old cache")
            ip_set = cache.get('KEEPER_CATALOG_MPG_IP_SET')
    else:
        logging.info("Get ips from cache...")
        ip_set = cache.get('KEEPER_CATALOG_MPG_IP_SET')
    return ip_set

def is_in_mpg_ip_range(ip):
    return IPAddress(ip) in get_mpg_ip_set()

def get_catalog():

    catalog = []

    repos_all = seafile_api.get_repo_list(0, MAX_INT)

    #repos_all = [seafile_api.get_repo('a6d4ae75-b063-40bf-a3d9-dde74623bb2c')]

    for repo in sorted(repos_all, key=lambda x: x.last_modify, reverse=True):

        try:
            proj = {}
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
                md = parse_markdown(file.get_content())
                if md:
                    # Author
                    a = md.get("Author")
                    if a:
                        a_list = strip_uni(a.strip()).split('\n')
                        authors = []
                        for _ in a_list:
                            author = {}
                            aa = _.split(';')
                            author['name'] = aa[0]
                            if len(aa) > 1 and aa[1].strip():
                                author['affs'] = [x.strip() for x in aa[1].split('|')]
                                author['affs'] = [x for x in author['affs'] if x ]
                            authors.append(author)
                        if a:
                            proj["authors"] = authors

                    # Description
                    d = strip_uni(md.get("Description"))
                    if d:
                        proj["description"] = d

                    # Comments
                    c = strip_uni(md.get("Comments"))
                    if c:
                        proj["comments"] = c

                    #Title
                    t = strip_uni(md.get("Title"))
                    if t:
                        proj["title"] = t
                        del proj["in_progress"]

                    proj["is_certified"] = is_certified_by_repo_id(repo.id)
            else:
                if DEBUG:
                    print "No %s for repo %s found" % (ARCHIVE_METADATA_TARGET, repo.name.encode("utf-8"))
            catalog.append(proj)

        except Exception as err:
            #msg = "repo_name: %s, id: %s, err: %s" % ( repo.name, repo.id, str(err) )
            msg = "repo_name: %s, id: %s" % ( repo.name.encode("utf-8"), repo.id  )
            logging.error (msg)
            logging.error(traceback.format_exc())
            if DEBUG:
                print msg

    return catalog


# if DEBUG:
    # print is_in_mpg_ip_range ('192.129.78.1')
    # print json.dumps(get_catalog(), indent=4, sort_keys=True, separators=(',', ': '))
