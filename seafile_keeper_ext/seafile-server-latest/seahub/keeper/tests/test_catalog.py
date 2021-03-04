import pytest
import json
import time
# import cchardet


from keeper.catalog.catalog_manager import is_in_mpg_ip_range, get_catalog, \
        generate_catalog, clean_up_catalog

from keeper.utils import get_user_name

from keeper.common import print_json
# @pytest.mark.skip
# def test_dummy():
    # pass

import django
django.setup()

# @pytest.mark.skip
def test_is_in_mpg_ip_range():
    is_in_mpg = is_in_mpg_ip_range('192.129.78.1')
    assert not is_in_mpg

# @pytest.mark.skip
def test_catalog():
    """Test catalog generation
    """
    start_time = time.time()
    catalog = get_catalog()
    print "--- %s seconds ---" % (time.time() - start_time)
    # for r in catalog:
        # if 'owner_name' in r and  'Vlad' in r['owner_name']:
            # print r
            # print json.dumps(r, indent=4, ensure_ascii = False, sort_keys=True, separators=(',', ': '))#.encode('utf8')
    # print json.dumps(catalog, ensure_ascii = False, indent=4, sort_keys=True, separators=(',', ': '))
    print "len:", len(catalog)


@pytest.mark.skip
def test_generate_catalog():
    """
        Test catalog generation
        Note: you prorbaly need to truncate keeper_catalog table
        TODO: move to catalog admin script
    """
    start_time = time.time()
    catalog = generate_catalog()
    print "--- %s seconds ---" % (time.time() - start_time)
    print_json(catalog)
    print "len:", len(catalog)

@pytest.mark.skip
def test_clean_up_catalog():
    """
        Test catalog clean up
        TODO: move to catalog admin script
    """
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "seahub.settings")

    import django
    django.setup()

    print "Deleted catalog entries: ", clean_up_catalog()


