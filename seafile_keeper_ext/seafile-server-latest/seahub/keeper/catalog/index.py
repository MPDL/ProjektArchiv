#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import urllib.request, urllib.error, urllib.parse
from urllib.parse import parse_qs
import math
import sys
import time
import io
import logging

import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "seahub.settings")
os.environ.setdefault("CCNET_CONF_DIR", "__SEAFILE_DIR__/ccnet")
os.environ.setdefault("SEAFILE_CONF_DIR", "__SEAFILE_DIR__/seafile-data")
os.environ.setdefault("SEAFILE_CENTRAL_CONF_DIR", "__SEAFILE_DIR__/conf")
os.environ.setdefault("SEAFES_DIR", "__SEAFILE_DIR__/seafile-server-latest/pro/python/seafes")


from django import template
from django.utils.translation import activate

from seahub.settings import SERVICE_URL, LOGO_PATH, SEAFILE_DIR, DEBUG
from keeper.catalog.catalog_manager import is_in_mpg_ip_range, get_catalog
from keeper.common import truncate_str

#########################
#                       #
#   start config vars   #
#                       #
#########################

# local install path of this script and files
install_path =  SEAFILE_DIR + '/seafile-server-latest/seahub/keeper/catalog/'

# all alloews ips or ip prefixes can be added here, empty string for all
allowed_ip_prefixes = []
# allowed_ip_prefixes = ['','172.16.1','10.10.','192.168.1.10','192.129.1.102']

# absolute url of json file with data of all projects
json_data_url = SERVICE_URL + '/api2/catalog/'

# path to cache json, make sure it is writable for script user
json_cache_file_path = install_path+'catalog.json'

# time to hold cache in minutes
json_cache_time = 0 # minutes

# items per page for pagination
pagination_items = 20 # per page

# max pages in paginator
max_pages_in_paginator = 5 # links


#########################
#                       #
#    end config vars    #
#                       #
#########################


def application(env, start_response):

    timer = time.time()


    # check static data (e.g. images)
    if ( 'static' in str(env['REQUEST_URI']) ):

        # send image header
        start_response('200 OK', [('Content-Type','image/png')])

        # image path
        tmp_static_path = install_path+str(env['REQUEST_URI'])[str(env['REQUEST_URI']).find('static'):]

        with open(tmp_static_path, 'rb') as tmp_static:

            # send response to web-server
            return [tmp_static.read()]

    else:
        # send html header
        start_response('200 OK', [('Content-Type','text/html')])

        # start response
        # TODO: close correctly!

        response = io.StringIO()

        with open(install_path + 'templates/catalog.html', 'r') as t_file:

            # default text if IP not allowed
            errmsg = 'Sie sind leider nicht berechtigt den Projektkatalog zu öffnen. Bitte wenden Sie sich an den Keeper Support.'

            # get HTTP_X_FORWARDED_FOR (i.e. servier is clustered), otherwise remote address
            remote_addr = env['HTTP_X_FORWARDED_FOR'] if 'HTTP_X_FORWARDED_FOR' in env else env['REMOTE_ADDR']

            is_valid_user = False

            # allow all
            if DEBUG:
                is_valid_user = True
                errmsg = ''
            else:
                # test for valid IP
                for allowed_ip_prefix in allowed_ip_prefixes:
                    if (remote_addr.startswith(allowed_ip_prefix)):
                        errmsg = ''
                        is_valid_user = True
                        break
                if not is_valid_user and is_in_mpg_ip_range(remote_addr):
                   errmsg = ''
                   is_valid_user = True

            results = []
            t = template.Template(t_file.read())
            ctx = {
                'errmsg': '',
                'logo_path' :  LOGO_PATH,
                'footer' : SEAFILE_DIR + '/seahub-data/custom/templates/keeper_footer.html',
            }
            
            if not is_valid_user or len(errmsg) > 0:
                # show ERROR message
                ctx.update(errmsg=errmsg)

            else:
                # show CATALOG
                get_params = parse_qs(env['QUERY_STRING'])

                # pars request params
                try:
                    request_body_size = int(env.get('CONTENT_LENGTH', 0))
                except (ValueError):
                    request_body_size = 0

                request_body = env['wsgi.input'].read()
                post_params = parse_qs(request_body)

                scope = 'with_metadata' # default
                if b'cat_scope' in post_params:
                    scope = post_params[b'cat_scope'][0].decode('utf-8')
                elif 'scope' in get_params:
                    scope = get_params['scope'][0]

                # jsondata = get_catalog(filter=scope[0])
                jsondata = get_catalog(scope)

                # load pagination parameter
                totalitemscount = 0
                pagination_current = 0
                try:
                    totalitemscount = len(jsondata)

                    #form = cgi.FieldStorage()
                    #pagination_current = int(form.getvalue('page'))
                    try:
                        if b'cat_scope' in post_params:
                            pagination_current = 0 # ignore error
                        elif (env['QUERY_STRING'] and 'page' in parse_qs(env['QUERY_STRING'])):
                            pagination_current = int(parse_qs(env['QUERY_STRING'])['page'][0])
                    except (RuntimeError, TypeError, NameError, ValueError):
                        pagination_current = 0 # ignore error

                    if ( pagination_current >= 1 ):
                        pagination_current = pagination_current-1
                    else:
                        pagination_current = 0
                except (RuntimeError, TypeError, NameError, ValueError):
                    pass  # ignore error


                # parse json an format data
                for i in range( (pagination_current*pagination_items), (pagination_current*pagination_items+pagination_items) ):
                    if ( i < len(jsondata) ):
                        results.append(jsondata[i])

                """
                Sample code:
                >>> from django import template
                >>> s = '<html>{% if test %}<h1>{{ varvalue }}</h1>{% endif %}</html>'
                >>> t = template.Template(s)

                (t is now a compiled template, and its render() method can be called multiple
                times with multiple contexts)

                >>> c = template.Context({'test':True, 'varvalue': 'Hello'})
                >>> t.render(c)
                '<html><h1>Hello</h1></html>'
                >>> c = template.Context({'test':False, 'varvalue': 'Hello'})
                >>> t.render(c)
                '<html></html>'
                """

                ctx.update({
                    'checked_'+scope: 'checked',
                    'results': [],
                })
                
                # set language, get it from cookies
                cookie = env.get('HTTP_COOKIE')
                'django_language=de' in cookie and activate('de')

                for res in results:

                    ctl = {}

                    ctl['repo_id'] = res['repo_id']
                    ctl['debug'] = repr(res)

                    title = "Project archive no. %s" % res['catalog_id']
                    if 'title' in res and len(res['title']) > 0:
                        title = truncate_str(res['title'], max_len=200)
                    ctl['title'] = '<h3><a href="%s">%s</a></h3>' % (res['landing_page_url'], title) \
                        if 'landing_page_url' in res else '<h3>%s</h3>' % title

                    ctl['landing_page_url'] = '<p><a href="%s">Landing Page</a></p>' % \
                        res['landing_page_url'] if 'landing_page_url' in res else ''

                    ctl['contact'] = '<p>Contact: %s</p>' % res['owner'].lower() \
                        if 'owner' in res else ''

                    author = []
                    if 'authors' in res:
                        for j in range(len(res['authors'])):
                            authors = res['authors'][j]
                            tmpauthor = ""
                            tmpauthors = authors['name'].title().split(', ')
                            for i in range(len(tmpauthors)):
                                if (i <= 0 and len(tmpauthors[i].strip()) > 1):
                                    tmpauthor += tmpauthors[i] + ", "
                                elif len(tmpauthors[i].strip()) > 1:
                                    tmpauthor += tmpauthors[i].strip()[:1] + "., "
                            tmpauthor = tmpauthor.strip()[:-1]

                            if (j >= 5):
                                tmpauthor = "et al."
                            author.append(tmpauthor)
                            if (j >= 5):
                                break

                            if 'affs' in authors:
                                author.append(','.join(authors['affs']).title())
                    ctl['author'] = '<p>%s</p>' % ', '.join(author)

                    desc = ''
                    if 'description' in res and len(res['description']) > 0:
                        desc = '<p>%s</p>' % truncate_str(res['description'], max_len=200)
                    ctl['description'] = desc

                    ctl['year'] = '<p>Year: %s</p>' % res['year'] \
                        if ('year' in res and len(res['year']) > 0) else ''

                    ctl['is_certified'] = 'is_certified' in res and res['is_certified']

                    ctx['results'].append(ctl)

                # PAGINATOR
                if totalitemscount > pagination_items:

                    ctx['data_nav'] = True

                    # max number of pages

                    max_pages_count = int(totalitemscount / pagination_items)\
                        if totalitemscount%pagination_items == 0  else\
                        int(totalitemscount / pagination_items) + 1

                    pagination_group = int(pagination_current / max_pages_in_paginator)
                    start_page = pagination_group * max_pages_in_paginator + 1
                    end_page = start_page + max_pages_in_paginator - 1
                    end_page = min(end_page, max_pages_count)

                    if pagination_current > 0:
                        ctx['page_prev'] = {
                            'page': str(pagination_current),
                            'scope': scope
                        }
                    if pagination_group > 1:
                        ctx['group_prev'] = {
                            'page': str((pagination_group - 1) * max_pages_in_paginator + 1),
                            'scope': scope
                        }
                    ctx['pagination'] = []
                    for i in range(start_page, end_page + 1):
                        ctx['pagination'].append({
                            'page': str(i),
                            'cssclass': 'active' if i - 1 == pagination_current else '',
                            'scope': scope
                        })
                    next_group_first_page = (pagination_group + 1) * max_pages_in_paginator + 1
                    if next_group_first_page < max_pages_count:
                        ctx['group_next'] = {
                            'page': str(next_group_first_page),
                            'scope': scope
                        }
                    if pagination_current + 1 < max_pages_count:
                        ctx['page_next'] = {
                            'page': str(pagination_current + 2),
                            'scope': scope
                        }

            response.write(t.render(template.Context(ctx)))

        # send response to web-server
        return(str(response.getvalue()+"\n<!-- render: "+str(time.time()-timer)+" -->\n").encode('utf-8'))

# end of file while is halt so

