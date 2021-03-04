# -*- coding: utf-8 -*-
import os
import pytest
from time import sleep
import tempfile
import json

import seahub.base
import django
django.setup()

from seaserv import seafile_api
from seafobj import commit_mgr, fs_mgr
from common import parse_markdown
from utils import get_user_name
from cdc.cdc_manager import quote_arg, validate, validate_institute, validate_author, CDC_PDF_PREFIX
from default_library_manager import copy_keeper_default_library, get_keeper_default_library
from seahub.settings import SERVER_EMAIL, ARCHIVE_METADATA_TARGET

from seahub.profile.models import Profile

from keepertestbase import create_tmp_user_with_profile, create_tmp_user, create_tmp_repo

MD_GOOD="""##Title
Title

## Author
Lastname, Firstname; Affiliation1

## Description
Description

## Year
2010

## Institute
INS; Department; Name, Fname
"""

MD_BAD="""##Title
Title

## Author
Lastname

## DescriptionXXXX
Description

## Year
2010XX

## InstituteXXXX
INS; Department; Name, Fname
"""

def get_root_dir(repo):
    commits = seafile_api.get_commit_list(repo.id, 0, 1)
    commit = commit_mgr.load_commit(repo.id, repo.version, commits[0].id)
    return fs_mgr.load_seafdir(repo.id, repo.version, commit.root_id)

def test_quote_arg():
    assert quote_arg('aaa') == "\"aaa\""

def test_get_user_name(create_tmp_user):
    """Test get user/profile with unicode
    """

    email = create_tmp_user
    print(email)
    assert email == Profile.objects.get_contact_email_by_user(email)

    nick = u"Vlad Влад Üäß 金属と金属の掛け合わせ"
    p = Profile.objects.add_or_update(email, nick)
    assert p.nickname == nick

    nick_from_db = get_user_name(email)
    assert nick == nick_from_db

    Profile.objects.delete_profile_by_user(email)

    print(json.dumps([nick_from_db], ensure_ascii = False, indent=4, sort_keys=True, separators=(',', ': ')))

def test_validate_author():
    """Lastname1, Firstname1; Affiliation11, Affiliation12, ...
    """
    assert validate_author("Makarenko, Vladislav; MPDL")
    assert validate_author("Van der Hus, Vincent; MPG")
    assert validate_author("Moreno Ortega, Silvana Anna; MPG")


def test_validate_institute():
    assert validate_institute("MPG; MPE; Name, FirstName")
    assert validate_institute("Max Planck Digital Library; DRG; Frank, Sander")
    assert validate_institute("Institute;Department;Name,F.")
    assert not validate_institute("Institute Department Name,F."), "Wrong institution string: No semicolons"

    assert validate_institute("Institute")
    assert validate_institute("Institute;")
    assert validate_institute("Institute; Department")
    assert validate_institute("Institute; Department;")
    assert validate_institute("Institute Long Name; Department Long Name")
    assert validate_institute("Institute Long Name; Department Long Name;")
    assert validate_institute("Institute; Department; Director")
    assert validate_institute("Institute; Department; Director With Long Name")
    assert validate_institute("Institute; Department; Director N.")
    assert validate_institute("Institute; Department; Director, N.")
    assert validate_institute("Institute Long Name; Department Long Name; Director, N.")
    assert validate_institute("Institute; Department; Director, N.;")
    assert validate_institute("Institute; Department; Director, , ,, N. ;; ; ")
    assert validate_institute("Institute Long Name; Department Long Name; Director, , N.; ")
    assert validate_institute("Institute Long Name; Department Long Name; Director, , Ivan Pupkin; ")
    assert validate_institute("Name; Department; Director forschungsgruppenleiter, Lastname or Abbr.")
    assert validate_institute("Наименование института; Департамент; Франк Сандер")

    assert not validate_institute("Na(me); Department; Petrov,,,, , ,  I.I."), "Not allowed symbol in institution name"
    assert not validate_institute("Name; Depa<rtmen>t; Petrov,,,, , ,  I.I."), "Not allowed symbol in departament name"
    assert not validate_institute("Name; Department; Petrov,,,, , ,  I.[I]."), "Not allowed symbol in director name"

    assert not validate_institute(None), "Empty institution string"
    assert not validate_institute("  "), "Empty institution string"


def test_validate_all():
    assert not validate(parse_markdown(MD_BAD))

def test_cdc_completely(create_tmp_repo):
    """Test CDC generation, complete workflow
    """

    repo = create_tmp_repo

    # TEST DEFAULT LIBRARY
    """check default library files are avialable"""
    kdl = get_keeper_default_library()
    if kdl:
        check_set = set([d.obj_name for d in kdl['dirents']])
    else:
        pytest.fail(msg="Default Library is empty, please install!")

    """copy library default files to lib"""
    copy_keeper_default_library(repo.id)
    sleep(2)

    # get copied files
    # commits = seafile_api.get_commit_list(repo.id, 0, 1)
    # commit = commit_mgr.load_commit(repo.id, repo.version, commits[0].id)
    # dir = fs_mgr.load_seafdir(repo.id, repo.version, commit.root_id)
    dir = get_root_dir(repo)



    # check copied files
    for fn in check_set:
        if not dir.lookup(fn):
            pytest.fail("Cannot find %s!" % fn)

    # TEST CDC GENERATION
    """add some txt file"""
    f = tempfile.NamedTemporaryFile()
    f.write('Text')
    f.flush()
    os.chmod(f.name, 0o666)

    seafile_api.post_file(repo.id, f.name, "/", "some_file.txt", SERVER_EMAIL)
    f.close()

    """update md file with correct fields"""
    f = tempfile.NamedTemporaryFile()
    f.write(MD_GOOD)
    f.flush()
    os.chmod(f.name, 0o666)

    seafile_api.put_file(repo.id, f.name, "/", ARCHIVE_METADATA_TARGET, SERVER_EMAIL, None)
    f.close()

    sleep(10)

    """check cdc pdf exists"""
    dir = get_root_dir(repo)
    cdc_pdfs = [f.name for f in dir.get_files_list() if f.name.startswith(CDC_PDF_PREFIX) and f.name.endswith('.pdf')]
    if not cdc_pdfs:
        pytest.fail("Cannot find cdc pdf in repo %s!" % repo.name)

    """check cdc pdf remove"""
    seafile_api.del_file(repo.id, "/", cdc_pdfs[0], SERVER_EMAIL)

    sleep(10)

    dir = get_root_dir(repo)
    cdc_pdfs = [f.name for f in dir.get_files_list() if f.name.startswith(CDC_PDF_PREFIX) and f.name.endswith('.pdf')]
    assert not cdc_pdfs, "cdc pdf should not be recreated if it has been deleted"

    """update md file with corrected field"""
    f = tempfile.NamedTemporaryFile()
    f.write(MD_GOOD.replace("2010", "2017"))
    f.flush()
    os.chmod(f.name, 0o666)

    seafile_api.put_file(repo.id, f.name, "/", ARCHIVE_METADATA_TARGET, SERVER_EMAIL, None)
    f.close()

    sleep(10)

    dir = get_root_dir(repo)
    cdc_pdfs = [f.name for f in dir.get_files_list() if f.name.startswith(CDC_PDF_PREFIX) and f.name.endswith('.pdf')]
    assert cdc_pdfs, "cdc pdf should be recreated if metadata md has been changed"
