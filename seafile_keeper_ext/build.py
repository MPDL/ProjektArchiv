#!/usr/bin/env python3
import os
import sys
import glob
import subprocess
import shutil
import re
import configparser
import pwd, grp
import getpass
import traceback

BACKUP_POSTFIX = '_orig'

########################
## Helper functions
########################

class InvalidAnswer(Exception):
    def __init__(self, msg):
        Exception.__init__(self)
        self.msg = msg
    def __str__(self):
        return self.msg

class Utils(object):

    all = False

    '''Groups all helper functions here'''
    @staticmethod
    def highlight(content):
        '''Add ANSI color to content to get it highlighted on terminal'''
        return '\x1b[33m%s\x1b[m' % content

    @staticmethod
    def red(content):
        '''Print red on terminal'''
        return '\x1b[31m%s\x1b[m' % content

    @staticmethod
    def info(msg, newline=True):
        sys.stdout.write(msg)
        if newline:
            sys.stdout.write('\n')

    @staticmethod
    def error(msg):
        '''Print error and exit'''
        print((Utils.red('Error: ' + msg)))
        sys.exit(1)

    @staticmethod
    def run_argv(argv, cwd=None, env=None, suppress_stdout=False, suppress_stderr=False):
        '''Run a program and wait it to finish, and return its exit code. The
        standard output of this program is supressed.

        '''
        with open(os.devnull, 'w') as devnull:
            if suppress_stdout:
                stdout = devnull
            else:
                stdout = sys.stdout

            if suppress_stderr:
                stderr = devnull
            else:
                stderr = sys.stderr

            proc = subprocess.Popen(argv,
                                    cwd=cwd,
                                    stdout=stdout,
                                    stderr=stderr,
                                    env=env)
            return proc.wait()

    @staticmethod
    def run(cmdline, cwd=None, env=None, suppress_stdout=False, suppress_stderr=False):
        '''Like run_argv but specify a command line string instead of argv'''
        with open(os.devnull, 'w') as devnull:
            if suppress_stdout:
                stdout = devnull
            else:
                stdout = sys.stdout

            if suppress_stderr:
                stderr = devnull
            else:
                stderr = sys.stderr

            proc = subprocess.Popen(cmdline,
                                    cwd=cwd,
                                    stdout=stdout,
                                    stderr=stderr,
                                    env=env,
                                    shell=True)
            return proc.wait()

    @staticmethod
    def prepend_env_value(name, value, env=None, seperator=':'):
        '''prepend a new value to a list'''
        if env is None:
            env = os.environ

        try:
            current_value = env[name]
        except KeyError:
            current_value = ''

        new_value = value
        if current_value:
            new_value += seperator + current_value

        env[name] = new_value

    @staticmethod
    def must_mkdir(path):
        '''Create a directory recursively, exit on failure'''
        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except OSError as e:
            Utils.error('failed to create directory %s:%s' % (path, e))

    @staticmethod
    def find_in_path(prog):
        if 'win32' in sys.platform:
            sep = ';'
        else:
            sep = ':'

        dirs = os.environ['PATH'].split(sep)
        for d in dirs:
            d = d.strip()
            if d == '':
                continue
            path = os.path.join(d, prog)
            if os.path.exists(path):
                return path

        return None

    @staticmethod
    def read_config(fn=None):
        '''Return a case sensitive ConfigParser by reading the file "fn"'''
        cp = configparser.ConfigParser(interpolation=None)
        cp.optionxform = str
        if fn:
            cp.read(fn)

        return cp

    @staticmethod
    def write_config(cp, fn):
        '''Return a case sensitive ConfigParser by reading the file "fn"'''
        with open(fn, 'w') as fp:
            cp.write(fp)

    @classmethod
    def ask_question(cls,
                     desc,
                     key=None,
                     note=None,
                     default=None,
                     validate=None,
                     yes_or_no=False,
                     password=False):
        '''Ask a question, return the answer.
        @desc description, e.g. "What is the port of ccnet?"

        @key a name to represent the target of the question, e.g. "port for
        ccnet server"

        @note additional information for the question, e.g. "Must be a valid
        port number"

        @default the default value of the question. If the default value is
        not None, when the user enter nothing and press [ENTER], the default
        value would be returned

        @validate a function that takes the user input as the only parameter
        and validate it. It should return a validated value, or throws an
        "InvalidAnswer" exception if the input is not valid.

        @yes_or_no If true, the user must answer "yes" or "no", and a boolean
        value would be returned

        @password If true, the user input would not be echoed to the
        console

        '''
        assert key or yes_or_no
        # Format description
        print()
        if note:
            desc += '\n' + note

        desc += '\n'
        if yes_or_no:
            desc += '[ yes, no or all ]'
        else:
            if default:
                desc += '[ default "%s" ]' % default
            else:
                desc += '[ %s ]' % key

        desc += ' '
        if cls.all:
            return True
        else:
            while True:
                # prompt for user input
                if password:
                    answer = getpass.getpass(desc).strip()
                else:
                    answer = input(desc).strip()

                # No user input: use default
                if not answer:
                    if default:
                        answer = default
                    else:
                        continue

                # Have user input: validate answer
                if yes_or_no:
                    if answer not in ['yes', 'no', 'y', 'n', 'all']:
                        print((Utils.highlight('\nPlease answer yes, no or all\n')))
                        continue
                    else:
                        if answer == 'all':
                            cls.all = True
                        return answer in ('yes', 'y', 'all')
                else:
                    if validate:
                        try:
                            return validate(answer)
                        except InvalidAnswer as e:
                            print((Utils.highlight('\n{}\n'.format(e))))
                            continue
                    else:
                        return answer


    @staticmethod
    def get_python_executable():
        '''Find a suitable python executable'''
        try_list = [
            'python3',
            'python3.6',
        ]


        for prog in try_list:
            path = Utils.find_in_path(prog)
            if path is not None:
                return path

        path = os.environ.get('PYTHON', 'python')

        if not path:
            Utils.error('Can not find python executable')

        return path

    @staticmethod
    def pkill(process):
        '''Kill the program with the given name'''
        argv = [
            'pkill', '-f', process
        ]

        Utils.run_argv(argv)


    @staticmethod
    def check_file(path):
        if not os.path.isfile(path):
            Utils.error("Cannot find file %s" % path)

    @staticmethod
    def check_dir(path):
        if not os.path.isdir(path):
            Utils.error("Cannot find dir %s" % path)


    @staticmethod
    def chown_symlink(path, group, user):
        """
        Chown symlink
        """
        gid = grp.getgrnam(group).gr_gid
        uid = pwd.getpwnam(user).pw_uid
        os.lchown(path, uid, gid)

    @staticmethod
    def set_perms(dirs, group, user):
        """
        Set permissions for dirs recursively
        """
        gid = grp.getgrnam(group).gr_gid
        uid = pwd.getpwnam(user).pw_uid
        for dir in dirs:
            os.chown(dir, gid, uid)
            os.chmod(dir, 0o755)
            for root, ds, fs in os.walk(dir):
                for d in ds:
                    p = os.path.join(root, d)
                    os.chown(p, gid, uid)
                    os.chmod(p, 0o755)
                for f in fs:
                    p = os.path.join(root, f)
                    os.chown(p, gid, uid)
                    if p.endswith(('py', 'sh')):
                        os.chmod(p, 0o755)


    @staticmethod
    def check_link(link, target):
        """
        True if link does not exist link and target exisist
        """
        print(("Check {}->{} ({},{})".format(link, target, not os.path.islink(link), os.path.exists(target))))

        return not os.path.islink(link) and os.path.exists(target)


        # return False

class EnvManager(object):
    '''System environment and directory layout'''
    def __init__(self):
        self.read_keeper_conf()
        self.set_seafile_env()
        self.set_keeper_env()

    def read_keeper_conf(self):
        '''Read keeper config file and set keeper related properties
           Note: keeper*.ini must be available! It can be symlink too.
        '''
        # conf_files = glob.glob(self.top_dir + '/keeper*.ini')
        conf_files = glob.glob('../../keeper*.ini')
        if not conf_files:
            Utils.error('Cannot find KEEPER config files')

        self.keeper_config = configparser.ConfigParser(interpolation=None)
        self.keeper_config.optionxform = str
        self.keeper_config.read_file(open(conf_files[0]))


    def set_seafile_env(self):

        # self.install_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.install_path = self.keeper_config.get('global', '__SEAFILE_DIR__')
        self.install_path = os.path.join(self.install_path, 'seafile-server-latest')

        self.top_dir = os.path.dirname(self.install_path)
        self.bin_dir = os.path.join(self.install_path, 'seafile', 'bin')
        self.central_config_dir = os.path.join(self.top_dir, 'conf')

        self.pro_data_dir = os.path.join(self.top_dir, 'pro-data')
        self.pro_program_dir = os.path.join(self.install_path, 'pro')
        self.pro_pylibs_dir = os.path.join(self.pro_program_dir, 'python')
        self.pro_misc_dir = os.path.join(self.pro_program_dir, 'misc')

        self.seafes_dir = os.path.join(self.pro_pylibs_dir, 'seafes')
        self.seahub_dir = os.path.join(self.install_path, 'seahub')

        self.ccnet_dir = os.path.join(self.top_dir, 'ccnet')
        self.seafile_dir = os.path.join(self.top_dir, 'seafile-data')
        self.central_config_dir = os.path.join(self.top_dir, 'conf')


    def get_seahub_env(self):
        '''Prepare for seahub syncdb'''
        env = dict(os.environ)
        env['CCNET_CONF_DIR'] = self.ccnet_dir
        env['SEAFILE_CONF_DIR'] = self.seafile_dir
        env['SEAFILE_CENTRAL_CONF_DIR'] = self.central_config_dir
        env['SEAFES_DIR'] = self.seafes_dir
        env['SEAHUB_DIR'] = self.seahub_dir
        self.setup_python_path(env)
        return env

    def set_keeper_env(self):

        self.SEAF_EXT_DIR_MAPPING = {
                # dir -> dir mappings
                'conf': os.path.join(self.top_dir, 'conf'),
                'seafile-server-latest': self.install_path,
                'seahub-data': os.path.join(self.top_dir, 'seahub-data'),
                'scripts': os.path.join(self.top_dir, 'scripts'),
                'http': os.path.join(self.keeper_config.get('http', '__HTTP_CONF_ROOT_DIR__'), 'sites-available'),
                # file -> file mappings
                'system/keepalived.conf': os.path.join('/etc', 'keepalived', 'keepalived.conf'),
                'system/cron.d.keeper': os.path.join('/etc', 'cron.d', 'cron-keeper'),
                'system/cron.d.keeper@background': os.path.join('/etc', 'cron.d', 'cron-keeper-background'),
                'system/memcached.conf': os.path.join('/etc', 'memcached.conf'),
                'system/memcached.service.d.local.conf': os.path.join('/etc', 'systemd', 'system', 'memcached.service.d', 'local.conf'),
                'system/keeper.service': os.path.join('/etc', 'systemd', 'system', 'keeper.service'),
                'system/keeper.service@background': os.path.join('/etc', 'systemd', 'system', 'keeper.service'),
                'system/keeper-oos-log.service': os.path.join('/etc', 'systemd', 'system', 'keeper-oos-log.service'),
		'system/keeper-env-vars.sh': os.path.join('/etc', 'profile.d', 'keeper-env-vars.sh'),
                'system/journald.conf': os.path.join('/etc', 'systemd', 'journald.conf'),
                'system/rsyslog.conf': os.path.join('/etc', 'rsyslog.conf'),
                'system/10-rsyslogd-remote.conf': os.path.join('/etc', 'rsyslog.d', '10-rsyslogd-remote.conf'),
                'system/my.cnf': os.path.join('/etc', 'mysql', 'my.cnf'),
                'system/my.cnf@single': os.path.join('/etc', 'mysql', 'my.cnf'),
                'system/nagios.keeper.cfg': os.path.join('/usr', 'local', 'nagios', 'libexec', 'seafile.cfg'),
                'system/nginx.conf': os.path.join('/etc', 'nginx', 'nginx.conf'),
                'system/phpmyadmin.conf': os.path.join('/etc', 'nginx', 'snippets', 'phpmyadmin.conf'),
                'system/clamd.conf': os.path.join('/etc', 'clamav', 'clamd.conf'),
                'system/clamav-daemon.service': os.path.join('/lib', 'systemd', 'system', 'clamav-daemon.service')
        }

        self.seafile_server_latest_target = os.path.join(self.top_dir, self.keeper_config.get('global', '__SEAFILE_SERVER_LATEST_DIR__'))

        self.seafile_logs_dir = os.path.join(self.top_dir, 'logs')

        self.custom_link = os.path.join(self.install_path, 'seahub', 'media', 'custom')
        self.custom_dir = os.path.join(self.top_dir, 'seahub-data', 'custom')

        self.avatars_link = os.path.join(self.install_path, 'seahub', 'media', 'avatars')
        self.avatars_dir = os.path.join(self.top_dir, 'seahub-data', 'avatars')

        self.django_admin_link = os.path.join('/usr', 'local', 'bin', 'django-admin')
        self.django_admin_path= os.path.join(os.path.realpath(self.install_path), 'seahub', 'thirdpart', 'bin', 'django-admin')

        self.assets_app_link = os.path.join(os.path.realpath(self.install_path), 'seahub', 'media', 'assets', 'scripts', 'app')
        self.assets_app_dir = os.path.join(os.path.realpath(self.install_path), 'seahub', 'static', 'scripts', 'app')

        self.assets_sysadmin_app_link = os.path.join(os.path.realpath(self.install_path), 'seahub', 'media', 'assets', 'scripts', 'sysadmin-app')
        self.assets_sysadmin_app_dir = os.path.join(os.path.realpath(self.install_path), 'seahub', 'static', 'scripts', 'sysadmin-app')

        self.keeper_service_link = os.path.join('/usr', 'local', 'bin', 'keeper-service')
        self.keeper_service_path= os.path.join(self.top_dir, 'scripts', 'keeper-service.sh')

        self.keeper_service_systemd_multi_user_target_wants_link = os.path.join('/etc', 'systemd', 'system', 'multi-user.target.wants', 'keeper.service')
        self.keeper_service_systemd_multi_user_target_wants_path = self.SEAF_EXT_DIR_MAPPING['system/keeper.service']

        self.keeper_oos_log_service_systemd_multi_user_target_wants_link = os.path.join('/etc', 'systemd', 'system', 'multi-user.target.wants', 'keeper-oos-log.service')
        self.keeper_oos_log_service_systemd_multi_user_target_wants_path = self.SEAF_EXT_DIR_MAPPING['system/keeper-oos-log.service']

        self.keeper_nagios_check_keeper_viruses_link = os.path.join('/usr', 'lib', 'nagios', 'plugins', 'check_keeper_viruses.sh')
        self.keeper_nagios_check_keeper_viruses_path = os.path.join(self.top_dir, 'scripts', 'monitoring', 'check_keeper_viruses.sh')

        self.keeper_nagios_check_keeper_elasticsearch_link = os.path.join('/usr', 'lib', 'nagios', 'plugins', 'check_es')
        self.keeper_nagios_check_keeper_elasticsearch_path = os.path.join(self.top_dir, 'scripts', 'monitoring', 'check_es.py')

        self.keeper_nagios_check_gpfs_health_link = os.path.join('/usr', 'lib', 'nagios', 'plugins', 'check_gpfs_health.sh')
        self.keeper_nagios_check_gpfs_health_path = os.path.join(self.top_dir, 'scripts', 'monitoring', 'check_gpfs_health.sh')

        self.keeper_nagios_check_tmp_link = os.path.join('/usr', 'lib', 'nagios', 'plugins', 'tmp-check.sh')
        self.keeper_nagios_check_tmp_path = os.path.join(self.top_dir, 'scripts', 'monitoring', 'check_tmp.sh')

        self.keeper_nagios_check_logfiles_link = os.path.join('/usr', 'lib', 'nagios', 'plugins', 'check_logfiles')
        self.keeper_nagios_check_logfiles_path = os.path.join(self.top_dir, 'scripts', 'monitoring', 'check_logfiles.pl')

        self.keeper_nagios_check_keeper_elasticsearch_link = os.path.join('/usr', 'lib', 'nagios', 'plugins', 'check_es')
        self.keeper_nagios_check_keeper_elasticsearch_path = os.path.join(self.top_dir, 'scripts', 'monitoring', 'check_es.py')

        self.keeper_nagios_check_gpfs_health_link = os.path.join('/usr', 'lib', 'nagios', 'plugins', 'check_gpfs_health.sh')
        self.keeper_nagios_check_gpfs_health_path = os.path.join(self.top_dir, 'scripts', 'monitoring', 'check_gpfs_health.sh')

        self.keeper_nagios_check_tmp_link = os.path.join('/usr', 'lib', 'nagios', 'plugins', 'tmp-check.sh')
        self.keeper_nagios_check_tmp_path = os.path.join(self.top_dir, 'scripts', 'monitoring', 'check_tmp.sh')

        self.keeper_nagios_check_logfiles_link = os.path.join('/usr', 'lib', 'nagios', 'plugins', 'check_logfiles')
        self.keeper_nagios_check_logfiles_path = os.path.join(self.top_dir, 'scripts', 'monitoring', 'check_logfiles.pl')

        self.keeper_ext_dir = os.path.join(self.top_dir, 'KEEPER', 'seafile_keeper_ext')

        self.keeper_var_log_dir = os.path.join('/var', 'log', 'keeper')

        self.keeper_tmp_dir = os.path.join('/run', 'tmp')



    def setup_python_path(self, env):
        '''And PYTHONPATH and CCNET_CONF_DIR/SEAFILE_CONF_DIR to env, which is
        needed by seahub

        '''
        extra_python_path = [
            self.pro_pylibs_dir,

            os.path.join(self.top_dir, 'conf'), # LDAP sync has to access seahub_settings.py
            os.path.join(self.install_path, 'seahub', 'thirdpart'),
            os.path.join(self.install_path, 'seahub-extra'),
            os.path.join(self.install_path, 'seahub-extra', 'thirdparts'),

            os.path.join(self.install_path, 'seafile/lib/python3.6/site-packages'),
        ]

        for path in extra_python_path:
            Utils.prepend_env_value('PYTHONPATH', path, env=env)

########################
## END helper functions
########################

def check_latest_link():
    """TODO: Docstring for check_latest_link.
    :returns: TODO

    """
    if not os.path.islink(env_mgr.install_path):
        Utils.error("Link {} does not exist!".format(env_mgr.install_path))

    if not os.path.exists(env_mgr.seafile_server_latest_target):
        Utils.error("seafile-server-latest target dir {} does not exist!".format(env_mgr.seafile_server_latest_target))



def do_links(link_target_list):
    """
    Create keeper related links
    """

    check_latest_link()

    for (link, target) in link_target_list:
        if Utils.check_link(link, target):
            # case for avatar link: link has same name as existed target dir
            # --> backup the dir
            if os.path.isdir(link):
                backup(link)

            try:
                os.symlink(target, link)
            except Exception:
                Utils.error("Cannot create link {} to target {}\n{}".format(link, target, traceback.format_exc()))

            Utils.chown_symlink(link, 'seafile', 'seafile')
            Utils.info(Utils.highlight("Created symlink {} -> {}".format(link, target)))


def expand_properties(content, path):
    kc = env_mgr.keeper_config
    node_type = kc.get('global', '__NODE_TYPE__').lower()
    is_background = node_type == 'background'
    for section in kc.sections():
        for key, value in kc.items(section):
           # capitalize bools
            if value.lower() in ('false', 'true') and path.endswith('.py'):
                value = value.capitalize()
            if key == '__EXTERNAL_ES_SERVER__':
                value = value.lower()
            # switch off webdav for BACKGROUND server
            if key == '__WEBDAV_ENABLED__' and is_background:
                value = 'false'
            # convert comma separated unicast peers to keepealived.conf valid value
            if key == '__MEMCACHED_KA_UNICAST_PEERS__' and ',' in value and path.endswith('keepalived.conf'):
                value = '\n'.join(value.split(','))
             # expand  __PROP__ and not ${__PROP__}
            content = re.sub(r"(?<!\$\{)(" + key + r")(?<!\})", value, content)

    #remove complete external_es_server setting complete from seafevents.conf on BACKGROUND node
    if is_background:
        content = re.sub("external_es_server.*?\n", "", content)

    #remove email smpt auth params for app nodes
    if node_type != 'single' and path.endswith('seahub_settings.py'):
        content = re.sub("EMAIL_HOST_USER.*?\n", "", content)
        content = re.sub("EMAIL_HOST_PASSWORD.*?\n", "", content)


    if kc.get('backup', '__IS_BACKUP_SERVER__').lower() == 'true':
        content = re.sub("backup_url.*?\n", "", content)
    else:
        content = re.sub("primary_url.*?\n", "", content)

    return content

def backup(path, mv=True):
    back_path = path + BACKUP_POSTFIX
    if os.path.exists(back_path):
        Utils.info("Backup already exists: {}, skipping!".format(path + BACKUP_POSTFIX))
    else:
        try:
            Utils.info("Backup {} to {}".format(path, back_path))
            if mv:
                os.rename(path, path + BACKUP_POSTFIX)
            else:
                shutil.copyfile(path, path + BACKUP_POSTFIX)
        except Exception as e:
            Utils.error("Cannot backup {}, error: {}".format(path, repr(e)))



def deploy_file(path, expand=False, dest_dir=None, skip_backup=False):

    Utils.check_file(path)

    # files to be ignored
    ignore_list = ('.gitignore')
    ignore_exts = ('.pyc', '.swp', '.bak')
    if os.path.basename(path) in ignore_list or path.endswith(ignore_exts):
        return

    p = path.strip('/').split('/')

    # file is in mapping
    if os.path.isfile(path) and path in env_mgr.SEAF_EXT_DIR_MAPPING:
        dest_dir = env_mgr.SEAF_EXT_DIR_MAPPING[path]
        dest_path = dest_dir
    else:
        # directory is in mapping
        if not dest_dir:
            if not p[0] in env_mgr.SEAF_EXT_DIR_MAPPING:
                Utils.error("Cannot find dest directory mapping for " + path)
            dest_dir = env_mgr.SEAF_EXT_DIR_MAPPING[p[0]]
        dest_path = dest_dir + '/' + '/'.join(p[1:])

    dest_dir = os.path.dirname(dest_path)

    if os.path.exists(dest_path):
        if skip_backup == False:
            backup(dest_path)
    else:
        if not Utils.ask_question("Deploy file {} into {}?".format(path, dest_path),
                                  default="yes",
                                  yes_or_no=True):
            return
        if not os.path.isdir(dest_dir):
            Utils.info("Create dir <{}>".format(dest_dir))
            Utils.must_mkdir(dest_dir)

    # black_list_exts = ('.jar', '.png', '.jpg', '.zip', '.svg', '.pdf', '.ttf', '.woff')
    # file types to be expanded
    white_list_ends = ('.conf', '.cfg', '.cnf', '.py', '.html', '.js', '.sh', '.css', '.txt', '.ini', '.service')
    # files to be expanded
    white_list_names = ('Makefile', 'cron-keeper', 'cron-keeper-background')
    if expand and (dest_path.endswith(white_list_ends) or os.path.basename(dest_path) in white_list_names):
        with open(path, 'r') as fin, open(dest_path, 'w') as fout:
            content = expand_properties(fin.read(), path)
            fout.write(content)
    else:
        shutil.copyfile(path, dest_path)
    Utils.info(Utils.highlight("%s has been deployed into %s%s" % (path, dest_path, " (expanded)" if expand else "")))

def deploy_dir(path, expand=False):

    Utils.check_dir(path)

    # dirs to be ignored
    ignore_list = ('.rope', '.cache', '__pycache__', '.git', 'tags', '.ropeproject', '.pytest_cache')
    if os.path.basename(path) in ignore_list:
        return

    for p in [p for p in os.listdir(path)]:
        sub_path = os.path.join(path, p)
        if os.path.isdir(sub_path):
            deploy_dir(sub_path, expand)
        else:
            deploy_file(sub_path, expand)

def deploy_http_conf():
    path = 'http'
    Utils.check_dir(path)
    opts = dict(env_mgr.keeper_config.items('http'))

    for file in [opts['__MAINTENANCE_HTTP_CONF__'], opts['__HTTP_CONF__']]:
        deploy_file('http/' + file, expand=True)

    deploy_file('http/' + opts['__MAINTENANCE_HTML__'], dest_dir=opts['__HTML_DEFAULT_DIR__'], expand=True)

    Utils.info("Note: enable/disable {} with nginx_ensite and nginx_dissite, see https://github.com/perusio/nginx_ensite for details".format(opts['__HTTP_CONF__']))

def deploy_ext():
    """
    Deploy keeper ext stuff
    """

    keep_ini = env_mgr.keeper_config

    ### deploy dirs
    for path in ('scripts', 'seahub-data', 'conf'):
        deploy_dir(path, expand=True)

    ### create ext-deploymnet related symlinks
    do_links((
        #(env_mgr.django_admin_link, env_mgr.django_admin_path),
        (env_mgr.custom_link, env_mgr.custom_dir),
        (env_mgr.avatars_link, env_mgr.avatars_dir),
    ))

    ### deploy seafile-serverl-latest
    deploy_dir('seafile-server-latest', expand=True)

    ### dist keeper
    Utils.run("make dist-keeper", cwd=env_mgr.seahub_dir, env=env_mgr.get_seahub_env())

    # TODO: remove, should be fixed in 6.3.12
    do_links((
        (env_mgr.assets_app_link, env_mgr.assets_app_dir),
        (env_mgr.assets_sysadmin_app_link, env_mgr.assets_sysadmin_app_dir),
    ))

    # create nagios checks links

    do_links((
        (env_mgr.keeper_nagios_check_keeper_viruses_link, env_mgr.keeper_nagios_check_keeper_viruses_path),
        (env_mgr.keeper_nagios_check_keeper_elasticsearch_link, env_mgr.keeper_nagios_check_keeper_elasticsearch_path),
        (env_mgr.keeper_nagios_check_gpfs_health_link, env_mgr.keeper_nagios_check_gpfs_health_path),
        (env_mgr.keeper_nagios_check_tmp_link, env_mgr.keeper_nagios_check_tmp_path),
        (env_mgr.keeper_nagios_check_logfiles_link, env_mgr.keeper_nagios_check_logfiles_path)
    ))

    # create seafile log dir
    Utils.must_mkdir(env_mgr.seafile_logs_dir)

    ### set chown and permissions for target dirs (ext related)

    Utils.set_perms(dirs=(
        env_mgr.ccnet_dir,
        env_mgr.SEAF_EXT_DIR_MAPPING['seahub-data'],
        env_mgr.central_config_dir,
        env_mgr.SEAF_EXT_DIR_MAPPING['scripts'],
        env_mgr.pro_data_dir,
        env_mgr.seafile_logs_dir,
        env_mgr.install_path,
        ),
        group=keep_ini.get('system', '__OS_GROUP__'),
        user=keep_ini.get('system', '__OS_USER__'),
    )

def deploy_system_conf():
    """
    Deploy keeper system confs
    """

    keep_ini = env_mgr.keeper_config


    # create keeper log dir
    Utils.must_mkdir(env_mgr.keeper_var_log_dir)

    ### set chown and permissions for target dirs (system related)
    Utils.set_perms(dirs=(
        env_mgr.keeper_var_log_dir,
        env_mgr.keeper_tmp_dir,
        ),
        group=keep_ini.get('system', '__OS_GROUP__'),
        user=keep_ini.get('system', '__OS_USER__'),
    )

    # deploy common confs
    deploy_file('system/nginx.conf', expand=True)
    deploy_file('system/phpmyadmin.conf', expand=True)
    deploy_file('system/rsyslog.conf', expand=True)
    deploy_file('system/10-rsyslogd-remote.conf', expand=True)
    deploy_file('system/my.cnf', expand=True)
    deploy_file('system/nagios.keeper.cfg',expand=True)
    deploy_file('system/keeper-env-vars.sh',expand=True)

    # deploy http confs
    deploy_http_conf()

    # deploy APP node related confs
    node_type = keep_ini.get('global', '__NODE_TYPE__')
    if node_type == 'APP':
        deploy_file('system/cron.d.keeper', expand=True, skip_backup=True)
        deploy_file('system/memcached.conf')
        deploy_file('system/keepalived.conf', expand=True)
        deploy_file('system/memcached.service.d.local.conf', expand=True)
        deploy_file('system/journald.conf', expand=True)
        deploy_file('system/keeper-oos-log.service', expand=True)
        os.chmod(env_mgr.SEAF_EXT_DIR_MAPPING['system/keeper-oos-log.service'], 0o755)
        do_links((
          (env_mgr.keeper_oos_log_service_systemd_multi_user_target_wants_link, env_mgr.keeper_oos_log_service_systemd_multi_user_target_wants_path),
        ))
        deploy_file('system/keeper.service')
        os.chmod(env_mgr.SEAF_EXT_DIR_MAPPING['system/keeper.service'], 0o755)


    if node_type in ('BACKGROUND', 'SINGLE'):
        deploy_file('system/cron.d.keeper@background', expand=True, skip_backup=True)
        deploy_file('system/clamd.conf', expand=True)
        deploy_file('system/clamav-daemon.service', expand=True)
        deploy_file('system/keeper.service@background')
        os.chmod(env_mgr.SEAF_EXT_DIR_MAPPING['system/keeper.service@background'], 0o755)


    if node_type in ('SINGLE'):
        deploy_file('system/my.cnf@single', expand=True)



    # create system symlinks
    do_links((
        (env_mgr.keeper_service_link, env_mgr.keeper_service_path),
        (env_mgr.keeper_service_systemd_multi_user_target_wants_link, env_mgr.keeper_service_systemd_multi_user_target_wants_path),
    ))


def run_services():

    keep_ini = env_mgr.keeper_config

    Utils.run('systemctl daemon-reload')
    Utils.run('systemctl restart rsyslog')
    Utils.run('systemctl restart systemd-journald')
    Utils.run('systemctl restart memcached')
    node_type = keep_ini.get('global', '__NODE_TYPE__')
    if node_type == 'APP':
      Utils.run('systemctl enable keeper-oos-log')
      Utils.run('systemctl start keeper-oos-log')




def do_deploy(args):

    if args.all:
        """
        Complete installation of the keeper on one node
        """

        ## Deploy whole keeper stuff
        Utils.info('do deploy --all')

        # global "yes" for all questions
        if args.yes:
            Utils.all = True

        deploy_ext()

        deploy_system_conf()

        run_services()


    elif args.conf:
        deploy_dir('conf', expand=True)
    elif args.ext:
        deploy_ext()
    elif args.http_conf:
        deploy_http_conf()
    elif args.system_conf:
        deploy_system_conf()
        run_services()
    else:
        if args.directory:
            for path in args.directory:
                deploy_dir(path, expand=args.expand)
        if args.file:
            for path in args.file:
                deploy_file(path, expand=args.expand)

        # check file

def do_restore(args):
    if args.seafile_src_to_ext:
        Utils.info('do seafile-src-to-ext')
    else:
        Utils.info('smth. else')

def do_generate(args):
    if args.msgen:
        Utils.info('Generate English translation catalog...')
        po_file = 'django.po'
        en_django_po_dir = os.path.join(env_mgr.keeper_ext_dir, 'seafile-server-latest', 'seahub', 'locale', 'en', 'LC_MESSAGES')
        backup(os.path.join(en_django_po_dir, po_file), mv=False)
        Utils.run("msgen {} > {}".format(po_file + BACKUP_POSTFIX, po_file), cwd=en_django_po_dir, env=env_mgr.get_seahub_env())
    elif args.i18n:
        Utils.info('Generate i18n...')
        Utils.run("make locale-keeper statici18n", cwd=env_mgr.seahub_dir, env=env_mgr.get_seahub_env())
        # Utils.run("make statici18n", cwd=env_mgr.seahub_dir, env=env_mgr.get_seahub_env())
        Utils.info('Done.')
    elif args.min_css:
        Utils.info('Generate seahub.min.css...')
        cmd = "yui-compressor -v seahub.css -o seahub.min.css"
        RC = Utils.run(cmd, cwd=os.path.join(env_mgr.seahub_dir, 'media', 'css'))
        if RC != 0:
            Utils.error("Cannot run {}, RC={}".format(cmd, RC))
    elif args.frontend:
        Utils.info('Generate frontend...')
        cmd = "sudo npm run build"
        RC = Utils.run(cmd, cwd=os.path.join(env_mgr.seahub_dir, 'frontend'))
        if RC != 0:
            Utils.error("Cannot run {}, RC={}".format(cmd, RC))
        else: 
            # copy frontend/build to ext by default
            args.frontend_build = True
            args.seafile_src_to_ext = False
            do_upgrade(args)
            # deploy assets
            Utils.run("sudo make collectstatic", cwd=env_mgr.seahub_dir, env=env_mgr.get_seahub_env())

def do_run(args):
    if args.frontend_dev:
        Utils.info('Run react.js dev server...')
        cmd = "npm run dev"
        RC = Utils.run(cmd, cwd=os.path.join(env_mgr.seahub_dir, 'frontend'))
        if RC != 0:
            Utils.error("Cannot run {}, RC={}".format(cmd, RC))

def do_upgrade(args):
    print('Upgrade...')
    # for root, dirs, files in os.walk(os.path.join(env_mgr.keeper_ext_dir, 'seafile-server-latest')):
    if args.seafile_src_to_ext:
        Utils.info("Copy seafile src files to ext")
        for root, dirs, files in os.walk('seafile-server-latest'):
            print((root, dirs, files))
            if  files and \
                not ('/keeper' in root
                    or '/.rope' in root or '/.cache' in root or '/__pycache__' in root
                    or '/.git' in root or '/tags' in root
                ):
                for file in files:
                    if not (file.endswith(('.pyc', '.png'))):
                        dest_path = os.path.join(root, file)
                        src_path = os.path.join(env_mgr.top_dir, dest_path)
                        if not os.path.exists(src_path):
                            Utils.info(Utils.highlight("File {} does not exist, please check".format(src_path)))
                        else:
                            Utils.info("Copy from {} to {}".format(src_path, dest_path))
                            shutil.copy(src_path, dest_path)
    elif args.frontend_build:
        Utils.info("Copy frontend/build files into ext")
        dest_dir = os.path.join(env_mgr.keeper_ext_dir, 'seafile-server-latest', 'seahub', 'frontend', 'build' )
        shutil.rmtree(dest_dir, ignore_errors=True)
        shutil.copytree(os.path.join(env_mgr.seafile_server_latest_target, 'seahub', 'frontend', 'build'), dest_dir, ignore=shutil.ignore_patterns('*.*' + BACKUP_POSTFIX))


env_mgr = EnvManager()

def main():
    try:
        import argparse
    except ImportError:
        sys.path.insert(0, glob.glob(os.path.join(env_mgr.pro_pylibs_dir, 'argparse*.egg'))[0])
        import argparse

    env_mgr.read_keeper_conf()

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(title='subcommands', description='')

    # deploy
    parser_deploy = subparsers.add_parser('deploy', help='Deploy KEEPER components')
    parser_deploy.add_argument('-e', '--expand', help='expand properties', action='store_true')
    parser_deploy.add_argument('-y', '--yes', help='say yes to all', action='store_true')
    parser_deploy = parser_deploy.add_mutually_exclusive_group()
    parser_deploy.set_defaults(func=do_deploy)
    parser_deploy.add_argument('--all', help='deploy all KEEPER components', action='store_true')
    parser_deploy.add_argument('--ext', help='deploy KEEPER ext sources', action='store_true')
    parser_deploy.add_argument('--conf', help='deploy conf files in KEEPER ~ext/conf directory', action='store_true')
    parser_deploy.add_argument('--http-conf', help='deploy http-confs', action='store_true')
    parser_deploy.add_argument('--system-conf', help='deploy all system conf files on the node, --http-conf is included', action='store_true')
    parser_deploy.add_argument('-f', '--file', help='deploy file(s)', nargs='+')
    parser_deploy.add_argument('-d', '--directory', help='deploy directory(s)', nargs='+')

    # restore
    # parser_restore = subparsers.add_parser('restore', help='Restore files')
    # parser_restore.set_defaults(func=do_restore)
    # parser_restore.add_argument('--seafile-src-to-ext', help='Restore all KEEPER files from overriden seafile src files', action='store_true')

    # upgrade
    parser_upgrade = subparsers.add_parser('upgrade', help='Upgrade KEEPER')
    parser_upgrade.set_defaults(func=do_upgrade)
    parser_upgrade.add_argument('--seafile-src-to-ext', help='''Upgrade KEEPER ext files to current Seafile sources.
                                Upgrade should be done BEFORE deploy-all command, on fresh untarred seafile-server files.
                                Upgraded files should be merged with the current KEEPER code!
                                Check https://keeper.mpdl.mpg.de/lib/a0b4567a-8f72-4680-8a76-6100b6ebbc3e/file/Keeper%%20System%%20Administration/Upgrade2Current-Seafie.md
                                ''', action='store_true')
    parser_upgrade.add_argument('--frontend-build', help='''Copied generated frontend/build files into KEEPER ext.
                                HowTo generate the build: https://keeper.mpdl.mpg.de/smart-link/50ae2e91-84e9-4fa5-b4b4-742fec4b095d/. 
                                ''', action='store_true')

    # generate
    parser_generate = subparsers.add_parser('generate', help='Generate components')
    parser_generate.set_defaults(func=do_generate)
    parser_generate.add_argument('--msgen', help='Create English translation catalog (i.e. copy msgid to msgstr in en/LC_MESSAGES/django.po)', action='store_true')
    parser_generate.add_argument('--i18n', help='Compile i18n files', action='store_true')
    parser_generate.add_argument('--min-css', help='''Generate min.css file for seahub.css.
                                 Please install yui-compressor: http://yui.github.io/yuicompressor in your system!
                                 ''', action='store_true')
    parser_generate.add_argument('--frontend', help='''Generate react.js application. Requirements: 
                                    1. install nodejs v10.20.1: https://www.digitalocean.com/community/tutorials/how-to-install-node-js-on-ubuntu-18-04-de#installation-mit-nvm
                                    2. cd ~latest/seahub/frontend && npm install
                                 ''', action='store_true')

    # run 
    parser_generate = subparsers.add_parser('run', help='Run development servers')
    parser_generate.set_defaults(func=do_run)
    parser_generate.add_argument('--frontend-dev', help='Run development server for frontend, see https://keeper.mpdl.mpg.de/smart-link/50ae2e91-84e9-4fa5-b4b4-742fec4b095d/', action='store_true')

    if len(sys.argv) == 1:
        print((parser.format_help()))
        return

    args = parser.parse_args()
    # print(args)
    args.func(args)


if __name__ == '__main__':
    main()
