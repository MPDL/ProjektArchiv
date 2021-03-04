SECRET_KEY = __SECRET_KEY__

# Debug mode
DEBUG = __DEBUG__

##########################################################################
#### Databases

# keeper db
KEEPER_DB_NAME = 'keeper-db'

DATABASE_ROUTERS = ['keeper.dbrouter.DbRouter',]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'seahub-db',
        'USER': '__DB_USER__',
        'PASSWORD': '__DB_PASSWORD__',
        'HOST': '__DB_HOST__',
        'PORT': '__DB_PORT__',
        'OPTIONS': {
            'init_command': 'SET default_storage_engine=INNODB',
        }
    },
    'keeper': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': KEEPER_DB_NAME,
        'USER': '__DB_USER__',
        'PASSWORD': '__DB_PASSWORD__',
        'HOST': '__DB_HOST__',
        'PORT': '__DB_PORT__',
        'OPTIONS': {
            'init_command': 'SET default_storage_engine=INNODB',
        }
    }
}

##########################################################################
#### Caches

CACHES = {
    'default': {
        'BACKEND': 'django_pylibmc.memcached.PyLibMCCache',
        'LOCATION': '__MEMCACHED_SERVER__',
    },
    'locmem': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}
COMPRESS_CACHE_BACKEND = 'locmem'
# COMPRESS_CACHE_BACKEND = 'django.core.cache.backends.locmem.LocMemCache'
##########################################################################
####  Logging

import os
LOG_DIR = os.environ.get('SEAHUB_LOG_DIR', '/tmp')
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s:%(lineno)s %(funcName)s %(message)s'
        },
        'syslog-django_request': {
            'format': '__NODE_FQDN__ django_request: %(asctime)s [%(levelname)s] %(name)s:%(lineno)s %(funcName)s %(message)s'
        },
        'syslog-seahub': {
            'format': '__NODE_FQDN__ seahub: %(asctime)s [%(levelname)s] %(name)s:%(lineno)s %(funcName)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
         }
     },
    'handlers': {
        'default': {
            'level':'DEBUG' if DEBUG else 'INFO',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'seahub.log'),
            'maxBytes': 1024*1024*10, # 10 MB
            'backupCount': 52,
            'formatter':'standard',
        },
        'request_handler': {
                'level':'INFO',
                'class':'logging.handlers.RotatingFileHandler',
                'filename': os.path.join(LOG_DIR, 'seahub_django_request.log'),
                'maxBytes': 1024*1024*10, # 10 MB
                'backupCount': 52,
                'formatter':'standard',
        },
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'post_office': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOG_DIR, 'post_office.log'),
            'maxBytes': 1024*1024*10, # 10 MB
            'backupCount': 52,
            'formatter': 'standard'
        },
        # 'syslog-django_request': {
            # 'level': 'INFO',
            # 'class': 'logging.handlers.SysLogHandler',
            # 'address': ('syslog-mpcdf.mpdl.mpg.de', 514),
            # 'facility': '__SYSLOG_FACILITY__',
            # 'formatter': 'syslog-django_request'
        # },
        # 'syslog-seahub': {
            # 'level': 'INFO',
            # 'class': 'logging.handlers.SysLogHandler',
            # 'address': ('syslog-mpcdf.mpdl.mpg.de', 514),
            # 'facility': '__SYSLOG_FACILITY__',
            # 'formatter': 'syslog-seahub'
        # },
    },
    'loggers': {
        '': {
            # 'handlers': ['default', 'syslog-seahub'],
            'handlers': ['default'],
            'level': 'INFO',
            'propagate': True
        },
        'django.request': {
            # 'handlers': ['request_handler', 'mail_admins', 'syslog-django_request'],
            'handlers': ['request_handler', 'mail_admins'],
            'level': 'INFO',
            'propagate': False
        },
        'post_office': {
            'handlers': ['post_office'],
            'level': 'DEBUG',
            'propagate': True
        },
    }
}

WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'frontend/',
        'STATS_FILE': os.path.join('__SEAFILE_DIR__', 'seafile-server-latest', 'seahub', 'frontend/webpack-stats.%s.json' % ('dev' if '__FRONTEND__' == 'dev' else 'pro')),
    }
}


# KEEPER Service URL
SERVICE_URL = '__SERVICE_URL__'

##########################################################################
#### Web server <-> file server

FILE_SERVER_ROOT = '__SERVICE_URL__/seafhttp'

##########################################################################
#### Cluster settings

AVATAR_FILE_STORAGE = 'seahub.base.database_storage.DatabaseStorage'

##########################################################################
#### User management options

# Enalbe or disalbe registration on web. Default is `False`.
ENABLE_SIGNUP = True

# Activate or deactivate user when registration complete. Default is `True`.
# If set to `False`, new users need to be activated by admin in admin panel.
ACTIVATE_AFTER_REGISTRATION = False

# Whether to send email when a system admin adding a new member. Default is `True`.
SEND_EMAIL_ON_ADDING_SYSTEM_MEMBER = True

# Whether to send email when a system admin resetting a user's password. Default is `True`.
SEND_EMAIL_ON_RESETTING_USER_PASSWD = True

# Send system admin notify email when user registration is complete. Default is `False`.
NOTIFY_ADMIN_AFTER_REGISTRATION = True

# Remember days for login. Default is 7
LOGIN_REMEMBER_DAYS = 7

# Attempt limit before showing a captcha when login.
LOGIN_ATTEMPT_LIMIT = 3

# deactivate user account when login attempts exceed limit
# Since version 5.1.2 or pro 5.1.3
FREEZE_USER_ON_LOGIN_FAILED = False

# mininum length for user's password
USER_PASSWORD_MIN_LENGTH = 6

# LEVEL based on four types of input:
# num, upper letter, lower letter, other symbols
# '3' means password must have at least 3 types of the above.
USER_PASSWORD_STRENGTH_LEVEL = 3

# default False, only check USER_PASSWORD_MIN_LENGTH
# when True, check password strength level, STRONG(or above) is allowed
USER_STRONG_PASSWORD_REQUIRED = True

# Force user to change password when admin add/reset a user.
# Added in 5.1.1, deafults to True.
FORCE_PASSWORD_CHANGE = True

# Age of cookie, in seconds (default: 2 weeks).
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7 * 2

# Whether a user's session cookie expires when the Web browser is closed.
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# Whether to save the session data on every request. Default is `False`
SESSION_SAVE_EVERY_REQUEST = False

# Whether enable personal wiki and group wiki. Default is `False`
# Since 6.1.0 CE
ENABLE_WIKI = True

##########################################################################
#### Repo snapshot label feature

# Turn on this option to let users to add a label to a library snapshot.
# Default is `False`
ENABLE_REPO_SNAPSHOT_LABEL = True


##########################################################################
#### Library options

# mininum length for password of encrypted library
REPO_PASSWORD_MIN_LENGTH = 8

# mininum length for password for share link (since version 4.4)
SHARE_LINK_PASSWORD_MIN_LENGTH = 8

# Disable sync with any folder. Default is `False`
# NOTE: since version 4.2.4
DISABLE_SYNC_WITH_ANY_FOLDER = False

# Enable or disable library history setting
ENABLE_REPO_HISTORY_SETTING = True

# Enable or disable normal user to create organization libraries
# Since version 5.0.5
ENABLE_USER_CREATE_ORG_REPO = False

# Enable or disable user share library to any group
# Since version 6.2.0
ENABLE_SHARE_TO_ALL_GROUPS = False


##########################################################################
#### Options for online file preview

# Whether to use pdf.js to view pdf files online. Default is `True`,  you can turn it off.
# NOTE: since version 1.4.
USE_PDFJS = True

# Online preview maximum file size, defaults to 30M.
# Note, this option controls files that can be previewed online, like pictures, txt, pdf.
# In pro edition, for preview doc/ppt/excel/pdf, there is another option `max-size`
# in seafevents.conf that controls the limit of files that can be previewed.
FILE_PREVIEW_MAX_SIZE = 30 * 1024 * 1024

# Extensions of previewed text files.
# NOTE: since version 6.1.1
TEXT_PREVIEW_EXT = """ac, am, bat, c, cc, cmake, cpp, cs, css, diff, el, h, html,
htm, java, js, json, less, make, org, php, pl, properties, py, rb,
scala, script, sh, sql, txt, text, tex, vi, vim, xhtml, xml, log, csv,
groovy, rst, patch, go"""

# Enable or disable thumbnails
# NOTE: since version 4.0.2
ENABLE_THUMBNAIL = True

# Seafile only generates thumbnails for images smaller than the following size.
THUMBNAIL_IMAGE_SIZE_LIMIT = 30 # MB

# Enable or disable thumbnail for video. ffmpeg and moviepy should be installed first.
# For details, please refer to https://manual.seafile.com/deploy/video_thumbnails.html
# NOTE: since version 6.1
ENABLE_VIDEO_THUMBNAIL = False

# Use the frame at 5 second as thumbnail
THUMBNAIL_VIDEO_FRAME_TIME = 5

# Absolute filesystem path to the directory that will hold thumbnail files.
THUMBNAIL_ROOT = '__SEAFILE_DIR__/seahub-data/thumbnail/thumb/'

# Default size for picture preview. Enlarge this size can improve the preview quality.
# NOTE: since version 6.1.1
THUMBNAIL_SIZE_FOR_ORIGINAL = 1024

##########################################################################
#### Cloud Mode

# Enable cloude mode and hide `Organization` tab.
CLOUD_MODE = True

# Disable global address book
ENABLE_GLOBAL_ADDRESSBOOK = True

##########################################################################
#### MULTI_TENANCY

# MULTI_TENANCY = True

ORG_MEMBER_QUOTA_ENABLED = True

##########################################################################
#### External authentication

# Enable authentication with ADFS
# Default is False
# Since 6.0.9
ENABLE_ADFS_LOGIN = False

# Enable authentication wit Kerberos
# Default is False
ENABLE_KRB5_LOGIN = False

# Enable authentication with Shibboleth
# Default is False
ENABLE_SHIB_LOGIN = __ENABLE_SHIB_LOGIN__

EXTRA_AUTHENTICATION_BACKENDS = (
    'shibboleth.backends.ShibbolethRemoteUserBackend',
)

SHIBBOLETH_ATTRIBUTE_MAP = {
    # Change eppn to mail if you use mail attribute for REMOTE_USER
    "eppn": (False, "username"),
}

SHIBBOLETH_ATTRIBUTE_MAP = {
    "eppn": (False, "username"),
    "givenName": (False, "givenname"),
    "sn": (False, "surname"),
    #"surname": (False, "surname"),
    "mail": (False, "contact_email"),
    "ou": (False, "institution"),
    #"o": (False, "institution"),
    #"institution": (False, "institution"),
    "affiliation": (False, "affiliation"),
}

SHIBBOLETH_AFFILIATION_ROLE_MAP = {
    'employee@mpdl.mpg.de': 'staff',
    'member@mpdl.mpg.de': 'staff',
    'student@mpdl.mpg.de': 'student',
    'employee@hu-berlin.de': 'guest'
}

ENABLE_GUEST_INVITATION = True

ENABLED_ROLE_PERMISSIONS = {
    'default': {
        'can_add_repo': True,
        'can_add_group': True,
        'can_view_org': True,
        'can_use_global_address_book': True,
        'can_generate_share_link': True,
        'can_generate_upload_link': True,
        'can_invite_guest': True,
        'can_connect_with_android_clients': True,
        'can_connect_with_ios_clients': True,
        'can_connect_with_desktop_clients': True,
        'can_send_share_link_mail': True,
        'role_quota': '1t',
    },
    'guest': {
        'can_add_repo': False,
        'can_add_group': False,
        'can_view_org': False,
        'can_use_global_address_book': False,
        'can_generate_share_link': False,
        'can_generate_upload_link': False,
        'can_invite_guest': False,
        'can_connect_with_android_clients': False,
        'can_connect_with_ios_clients': False,
        'can_connect_with_desktop_clients': False,
     #   'role_quota': '',
    },
    'staff': {
        'can_add_repo': True,
        'can_add_group': True,
        'can_view_org': True,
        'can_use_global_address_book': True,
        'can_generate_share_link': True,
        'can_generate_upload_link': True,
        'can_invite_guest': True,
        'can_connect_with_android_clients': True,
        'can_connect_with_ios_clients': True,
        'can_connect_with_desktop_clients': True,
        'can_send_share_link_mail': True,
        'role_quota': '1t',
    },
}

ENABLED_ADMIN_ROLE_PERMISSIONS = {
    'users_and_logs_manager': {
        'can_view_system_info': True,
        'can_view_statistic': True,
        'can_manage_user': True,
        'can_view_user_log': True,
        'can_view_admin_log': True,
        'other_permission': True,
    },
}

##########################################################################
#### Other

# Disable settings via Web interface in system admin->settings
# Default is True
# Since 5.1.3
ENABLE_SETTINGS_VIA_WEB = False

# Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Berlin'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
# Default language for sending emails.
LANGUAGE_CODE = 'en'

# Set this to your website/company's name. This is contained in email notifications and welcome message when user login for the first time.
SITE_NAME = 'KEEPER'

# Browser tab's title
SITE_TITLE = 'KEEPER'

# If you don't want to run seahub website on your site's root path, set this option to your preferred path.
# e.g. setting it to '/seahub/' would run seahub on http://example.com/seahub/.
SITE_ROOT = '/'

# Max number of files when user upload file/folder.
# Since version 6.0.4
MAX_NUMBER_OF_FILES_FOR_FILEUPLOAD = 500

# Control the language that send email. Default to user's current language.
# Since version 6.1.1
SHARE_LINK_EMAIL_LANGUAGE = ''

# Interval for browser requests unread notifications
# Since PRO 6.1.4 or CE 6.1.2
UNREAD_NOTIFICATIONS_REQUEST_INTERVAL = 3 * 60 # seconds

# enable 'upload folder' or not
ENABLE_UPLOAD_FOLDER = True

# Override language settings
LANGUAGES = (
    ('de', 'Deutsch'),
    ('en', 'English'),
)



##########################################################################
#### Pro edition only options

# Whether to show the used traffic in user's profile popup dialog. Default is True
SHOW_TRAFFIC = True

# Allow administrator to view user's file in UNENCRYPTED libraries
# through Libraries page in System Admin. Default is False.
ENABLE_SYS_ADMIN_VIEW_REPO = False

# For un-login users, providing an email before downloading or uploading on shared link page.
# Since version 5.1.4
ENABLE_SHARE_LINK_AUDIT = False

# Check virus after upload files to shared upload links. Defaults to `False`.
# Since version 6.0
ENABLE_UPLOAD_LINK_VIRUS_CHECK = False

# Enable system admin add T&C, all users need to accept terms before using. Defaults to `False`.
# Since version 6.0
ENABLE_TERMS_AND_CONDITIONS = True

# Enable two factor authentication for accounts. Defaults to `False`.
# Since version 6.0
ENABLE_TWO_FACTOR_AUTH = True

# Enable user select a template when he/she creates library.
# When user select a template, Seafile will create folders releated to the pattern automaticly.
# Since version 6.0
# LIBRARY_TEMPLATES = {
    # 'Technology': ['/Develop/Python', '/Test'],
    # 'Finance': ['/Current assets', '/Fixed assets/Computer']
# }

# Send email to these email addresses when a virus is detected.
# This list can be any valid email address, not necessarily the emails of Seafile user.
# Since version 6.0.8
VIRUS_SCAN_NOTIFY_LIST = ['__SERVER_EMAIL__']

##########################################################################
#### KEEPER branding settings

BRANDING_CSS = 'custom/__BRANDING_CSS__'

LOGO_PATH = 'custom/__LOGO_IMG__'
CUSTOM_LOGO_PATH = 'custom/__LOGO_IMG__'
LOGO_WIDTH = 140
LOGO_HEIGHT = 40

FAVICON_PATH = 'img/favicon.png'
CUSTOM_FAVICON_PATH = 'img/favicon.png'

DESKTOP_CUSTOM_LOGO = 'custom/keeper-client-logo.png'
DESKTOP_CUSTOM_BRAND = 'KEEPER'

# MPDL EMAIL settings

##########################################################################
#### Email settings

EMAIL_USE_TLS = True
EMAIL_HOST = '__EMAIL_HOST__'        # smpt server
EMAIL_PORT = '__EMAIL_PORT__'
DEFAULT_FROM_EMAIL = '__DEFAULT_FROM_EMAIL__'
SERVER_EMAIL = '__SERVER_EMAIL__'
#settings only for BACKGROUND & SINGLE, removed APPs by build.py
EMAIL_HOST_USER = '__EMAIL_HOST_USER__'    # username and domain
EMAIL_HOST_PASSWORD = '__EMAIL_HOST_PASSWORD__'    # password

##########################################################################
#### Multiple Organization/Institution User Management, see http://manual.seafile.com/deploy_pro/multi_institutions.html

MULTI_INSTITUTION = True

EXTRA_MIDDLEWARE_CLASSES = (
    'seahub.institutions.middleware.InstitutionMiddleware',
    'shibboleth.middleware.ShibbolethRemoteUserMiddleware',
    'seahub_extra.organizations.middleware.RedirectMiddleware',
)

EXTRA_AUTHENTICATION_BACKENDS = (
    'seahub_extra.django_cas_ng.backends.CASBackend',
)

# Settings for background node
OFFICE_CONVERTOR_NODE = __IS_OFFICE_CONVERTOR_NODE__

OFFICE_CONVERTOR_ROOT = '__BACKGROUND_SERVER__'

# Enable LibreOffice Online
ENABLE_OFFICE_WEB_APP = __ENABLE_OFFICE_WEB_APP__

# Url of LibreOffice Online's discovery page
# The discovery page tells Seafile how to interact with LibreOffice Online when view file online
OFFICE_WEB_APP_BASE_URL = '__OFFICE_WEB_APP_BASE_URL__'

# Expiration of WOPI access token
# WOPI access token is a string used by Seafile to determine the file's
# identity and permissions when use LibreOffice Online view it online
# And for security reason, this token should expire after a set time period
WOPI_ACCESS_TOKEN_EXPIRATION = 30 * 60   # seconds

# List of file formats that you want to view through LibreOffice Online
# You can change this value according to your preferences
# And of course you should make sure your LibreOffice Online supports to preview
# the files with the specified extensions
OFFICE_WEB_APP_FILE_EXTENSION = ( 'doc', 'docm', 'dotm', 'dotx', 'xls', 'xlsm', 'ppt', 'pps', 'pptm', 'potm', 'ppam', 'potx', 'ppsm', 'odt', 'ods', 'fodp', 'fods', 'fodt', 'odp' )

# Enable edit files through LibreOffice Online
ENABLE_OFFICE_WEB_APP_EDIT = True

# types of files should be editable through LibreOffice Online
OFFICE_WEB_APP_EDIT_FILE_EXTENSION = ( 'xlsx','xlsb', 'pptx', 'docx' )

# Admin users page default sorting

ALWAYS_SORT_USERS_BY_QUOTA_USAGE =  True

# Enable Onlyoffice
ENABLE_ONLYOFFICE = __ENABLE_ONLYOFFICE__
VERIFY_ONLYOFFICE_CERTIFICATE = True

# OnlyIffice settings
ONLYOFFICE_APIJS_URL = '__ONLYOFFICE_APIJS_URL__'
ONLYOFFICE_FILE_EXTENSION = ('doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx', 'odt', 'fodt', 'odp', 'fodp', 'ods', 'fods')
ONLYOFFICE_EDIT_FILE_EXTENSION = ('docx', 'pptx', 'xlsx')
ONLYOFFICE_JWT_SECRET = '__ONLYOFFICE_JWT_SECRET__'


##########################################################################
####  KEEPER specific settings

# Keeper root dir
SEAFILE_DIR = '__SEAFILE_DIR__'

# Keeper logging
KEEPER_LOG_DIR = '__KEEPER_LOG_DIR__'

# SINGLE_MODE
SINGLE_MODE = '__NODE_TYPE__' == 'SINGLE'

# default filename for CDC metadata
ARCHIVE_METADATA_TARGET = 'archive-metadata.md'

# default KEEPER library name
KEEPER_DEFAULT_LIBRARY = 'Keeper Default Library'

# Keeper DOI integration
DOI_SERVER = '__DOI_SERVER__'
DOI_USER = '__DOI_USER__'
DOI_PASSWORD = '__DOI_PASSWORD__'
DOI_TIMEOUT = __DOI_TIMEOUT__

# archiving
KEEPER_ARCHIVING_ROOT = 'http://__NODE_FQDN__' if SINGLE_MODE else '__KEEPER_ARCHIVING_ROOT__'
KEEPER_ARCHIVING_PORT = '__KEEPER_ARCHIVING_PORT__'
KEEPER_ARCHIVING_NODE = KEEPER_ARCHIVING_ROOT == 'http://__NODE_FQDN__'

# KEEPER external resources
KEEPER_MPG_DOMAINS_URL = '__KEEPER_MPG_DOMAINS_URL__'
KEEPER_MPG_IP_LIST_URL = '__KEEPER_MPG_IP_LIST_URL__'

# Keepear bloxberg integration
BLOXBERG_SERVER = '__BLOXBERG_SERVER__'

TEST_SERVER='__TEST_SERVER__'
TEST_SERVER_ADMIN='__TEST_SERVER_ADMIN__'
TEST_SERVER_PASSWORD="__TEST_SERVER_ADMIN_PASSWORD__"
