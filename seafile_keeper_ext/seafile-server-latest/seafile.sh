#!/bin/bash

### BEGIN INIT INFO
# Provides:          seafile
# Required-Start:    $local_fs $remote_fs $network
# Required-Stop:     $local_fs
# Default-Start:     1 2 3 4 5
# Default-Stop:
# Short-Description: Starts Seafile Server
# Description:       starts Seafile Server
### END INIT INFO

echo ""

SCRIPT=$(readlink -f "$0")
INSTALLPATH=$(dirname "${SCRIPT}")
TOPDIR=$(dirname "${INSTALLPATH}")
default_ccnet_conf_dir=${TOPDIR}/ccnet
central_config_dir=${TOPDIR}/conf
seaf_controller="${INSTALLPATH}/seafile/bin/seafile-controller"


export PATH=${INSTALLPATH}/seafile/bin:$PATH
export ORIG_LD_LIBRARY_PATH=${LD_LIBRARY_PATH}
export SEAFILE_LD_LIBRARY_PATH=${INSTALLPATH}/seafile/lib/:${INSTALLPATH}/seafile/lib64:${LD_LIBRARY_PATH}

script_name=$0
function usage () {
    echo "usage : "
    echo "$(basename ${script_name}) { start | stop | restart } "
    echo ""
}

# check args
if [[ $# != 1 || ( "$1" != "start" && "$1" != "stop" && "$1" != "restart" ) ]]; then
    usage;
    exit 1;
fi

function validate_running_user () {
    real_data_dir=`readlink -f ${seafile_data_dir}`
    running_user=`id -un`
    data_dir_owner=`stat -c %U ${real_data_dir}`

    if [[ "${running_user}" != "${data_dir_owner}" ]]; then
        echo "Error: the user running the script (\"${running_user}\") is not the owner of \"${real_data_dir}\" folder, you should use the user \"${data_dir_owner}\" to run the script."
        exit -1;
    fi
}

function check_python_executable() {
    if [[ "$PYTHON" != "" && -x $PYTHON ]]; then
        return 0
    fi

    if which python2.7 2>/dev/null 1>&2; then
        PYTHON=python2.7
    elif which python27 2>/dev/null 1>&2; then
        PYTHON=python27
    elif which python2.6 2>/dev/null 1>&2; then
        PYTHON=python2.6
    elif which python26 2>/dev/null 1>&2; then
        PYTHON=python26
    else
        echo
        echo "Can't find a python executable of version 2.6 or above in PATH"
        echo "Install python 2.6+ before continue."
        echo "Or if you installed it in a non-standard PATH, set the PYTHON enviroment varirable to it"
        echo
        exit 1
    fi
}

check_python_executable;

export PYTHONPATH=${INSTALLPATH}/seafile/lib/python2.6/site-packages:${INSTALLPATH}/seafile/lib64/python2.6/site-packages:${INSTALLPATH}/seahub/thirdpart:$PYTHONPATH
export PYTHONPATH=${INSTALLPATH}/seafile/lib/python2.7/site-packages:${INSTALLPATH}/seafile/lib64/python2.7/site-packages:$PYTHONPATH
export PYTHONPATH=$PYTHONPATH:$pro_pylibs_dir
export PYTHONPATH=$PYTHONPATH:${INSTALLPATH}/seahub-extra/
export PYTHONPATH=$PYTHONPATH:${INSTALLPATH}/seahub-extra/thirdparts

function validate_ccnet_conf_dir () {
    if [[ ! -d ${default_ccnet_conf_dir} ]]; then
        echo "Error: there is no ccnet config directory."
        echo "Have you run setup-seafile.sh before this?"
        echo ""
        exit -1;
    fi
}

function validate_central_conf_dir () {
    if [[ ! -d ${central_config_dir} ]]; then
        echo "Error: there is no conf/ directory."
        echo "Have you run setup-seafile.sh before this?"
        echo ""
        exit -1;
    fi
}

function read_seafile_data_dir () {
    seafile_ini=${default_ccnet_conf_dir}/seafile.ini
    if [[ ! -f ${seafile_ini} ]]; then
        echo "${seafile_ini} not found. Now quit"
        exit 1
    fi
    seafile_data_dir=$(cat "${seafile_ini}")
    if [[ ! -d ${seafile_data_dir} ]]; then
        echo "Your seafile server data directory \"${seafile_data_dir}\" is invalid or doesn't exits."
        echo "Please check it first, or create this directory yourself."
        echo ""
        exit 1;
    fi
}

function test_config() {
    if ! LD_LIBRARY_PATH=$SEAFILE_LD_LIBRARY_PATH ${seaf_controller} --test \
         -c "${default_ccnet_conf_dir}" \
         -d "${seafile_data_dir}" \
         -F "${central_config_dir}" ; then
        exit 1;
    fi
}

function check_component_running() {
    name=$1
    cmd=$2
    if pid=$(pgrep -f "$cmd" 2>/dev/null); then
        echo "[$name] is running, pid $pid. You can stop it by: "
        echo
        echo "        kill $pid"
        echo
        echo "Stop it and try again."
        echo
        exit
    fi
}

function validate_already_running () {
    if pid=$(pgrep -f "seafile-controller -c ${default_ccnet_conf_dir}" 2>/dev/null); then
        echo "Seafile controller is already running, pid $pid"
        echo
        exit 1;
    fi

    check_component_running "ccnet-server" "ccnet-server -c ${default_ccnet_conf_dir}"
    check_component_running "seaf-server" "seaf-server -c ${default_ccnet_conf_dir}"
    check_component_running "fileserver" "fileserver -c ${default_ccnet_conf_dir}"
    check_component_running "seafdav" "wsgidav.server.run_server"
    check_component_running "seafevents" "seafevents.main --config-file ${central_config_dir}"
}

function test_java {
    if ! which java 2>/dev/null 1>&2; then
        echo "java is not found on your machine. Please install it first."
        exit 1;
    fi
}

function start_seafile_server () {
    validate_already_running;
    validate_central_conf_dir;
    validate_ccnet_conf_dir;
    read_seafile_data_dir;
    validate_running_user;
    test_config;
    test_java;

    export PYTHON_EGG_CACHE=${seafile_data_dir}/.cache/Python-Egg

    echo "Starting seafile server, please wait ..."

    mkdir -p $TOPDIR/logs
    if ! LD_LIBRARY_PATH=$SEAFILE_LD_LIBRARY_PATH ${seaf_controller} -c "${default_ccnet_conf_dir}" -d "${seafile_data_dir}" -F "${central_config_dir}"; then
        controller_log="$seafile_data_dir/controller.log"
        echo
        echo "Failed to start seafile server. See $controller_log for more details."
        echo
        exit 1
    fi

    sleep 3

    # check if seafile server started successfully
    if ! pgrep -f "seafile-controller -c ${default_ccnet_conf_dir}" 2>/dev/null 1>&2; then
        echo "Failed to start seafile server"
        exit 1;
    fi

    echo "Seafile server started"
    echo
}

function kill_all () {
    pkill -f "ccnet-server -c ${default_ccnet_conf_dir}"
    pkill -f "seaf-server -c ${default_ccnet_conf_dir}"
    pkill -f "fileserver -c ${default_ccnet_conf_dir}"
    pkill -f "seafevents.main"
    pkill -f "soffice.*--invisible --nocrashreport"
    pkill -f  "wsgidav.server.run_server"
}

function stop_seafile_server () {
    if ! pgrep -f "seafile-controller -c ${default_ccnet_conf_dir}" 2>/dev/null 1>&2; then
        echo "seafile server not running yet"
        kill_all
        return 1
    fi

    echo "Stopping seafile server ..."
    pkill -SIGTERM -f "seafile-controller -c ${default_ccnet_conf_dir}"
    kill_all

    return 0
}

function restart_seafile_server () {
    stop_seafile_server;
    sleep 5
    start_seafile_server;
}

case $1 in
    "start" )
        start_seafile_server;
        ;;
    "stop" )
        stop_seafile_server;
        ;;
    "restart" )
        restart_seafile_server;
esac

echo "Done."
