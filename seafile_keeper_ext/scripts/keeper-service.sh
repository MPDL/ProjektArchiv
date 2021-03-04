#!/bin/bash

### BEGIN INIT INFO
# Provides:          seafile-server
# Required-Start:    $local_fs $remote_fs $network
# Required-Stop:     $local_fs
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Starts Seafile Server
# Description:       starts Seafile Server
### END INIT INFO

#set -x

CURR_DIR=$(dirname $(readlink -f $0))
source "${CURR_DIR}/inject_keeper_env.sh"
if [ $? -ne 0  ]; then
	echo "Cannot run inject_keeper_env.sh"
    exit 1
fi

# Change the value of "user" to linux user name who runs seafile
user=${__OS_USER__}
group=${__OS_GROUP__}

WEB_SERVER=${__HTTP_SERVER__}

# Change the value of "seafile_dir" to your path of seafile installation
# usually the home directory of $user
seafile_dir=${__SEAFILE_DIR__}
script_path=${seafile_dir}/seafile-server-latest
seafile_init_log=${seafile_dir}/logs/seafile.init.log
seahub_init_log=${seafile_dir}/logs/seahub.init.log
background_init_log=${seafile_dir}/logs/background.init.log
default_ccnet_conf_dir=${seafile_dir}/ccnet

USR_CTX="sudo -iu ${user}"
ROOT_CTX="sudo -i"

function check_gpfs() {
    [[ $(ls /keeper) =~ "Stale file handle" ]] && err_and_exit "Stale file handle"
    [ ! -d "/keeper" ] &&  err_and_exit "Cannot access /keeper"
    echo_green "/dev/gpfs_keeper is OK"
}


function restart_gpfs () {
    $0 status
    [ $? -eq 0 ] && err_and_exit "Keeper is running, please shutdown it first"
    mmshutdown && mmstartup
    sleep 10
    check_gpfs 
}

function check_en_dis_nginx () {
    RESULT=$(type "nginx_ensite" 2>/dev/null)
    if [ $? -ne 0 ] ; then
        err_and_exit "Please install nginx_[en|dis]site: https://github.com/perusio/nginx_ensite"
    fi
}
function check_mysql () {
    RESULT=$(systemctl status mysql.service)
    if [ $? -ne 0 ] ; then
        warn "mysql is not running, please check!"
    fi
}
function check_puppet () {
    RESULT=$(type "puppet" 2>/dev/null)
    if [ $? -eq 0 ] ; then
        RESULT=$(cat $(puppet config print vardir)/state/agent_disabled.lock 2>&1)
        [[ $RESULT == *"No such file or directory"* ]] && warn "puppet agent is runnig"
    fi

}

function check_memcached () {
# for the cluster the memcached runs in single instance mode 
    RESULT=$(echo stats | nc -q 2 ${__MEMCACHED_SERVER__%:*} ${__MEMCACHED_SERVER__#*:} 2>/dev/null | grep -Eq "STAT pid [0-9]+")
    if [ $? -ne 0 ] ; then
        warn "memcached is not running on ${__MEMCACHED_SERVER__}, please check!"
    fi
}

function check_keepalived () {
    RESULT=$(type "keepalived" 2>/dev/null)
    if [ $? -eq 0 ] ; then
        RESULT=$(systemctl is-active keepalived.service)
        [[ $RESULT != "active" ]] && warn "keepalived is not runnig on the node"
    fi
}

# switch HTTP configurations between default and maintenance
function switch_maintenance_mode () {
	local TO_DIS="${__MAINTENANCE_HTTP_CONF__}"
	local TO_EN="${__HTTP_CONF__}" 
	
	if [ -L "${__HTTP_CONF_ROOT_DIR__}/sites-enabled/$TO_EN" ]; then
		TO_DIS="${__HTTP_CONF__}"
		TO_EN="${__MAINTENANCE_HTTP_CONF__}"
	fi	

	nginx_dissite $TO_DIS
	if [ $? -ne 0  ]; then
		err_and_exit "Cannot disable HTTP config $TO_DIS"
	fi
	
	nginx_ensite $TO_EN
	if [ $? -ne 0  ]; then
		err_and_exit "Cannot enable HTTP config $TO_EN"
	fi

	service nginx reload
	if [ $? -ne 0  ]; then
		err_and_exit "Cannot reload HTTP $TO_EN"
	fi
}

function check_component_running() {
    name=$1
    cmd=$2
    if pid=$(pgrep -f "$cmd" 2>/dev/null); then
        echo "[$name] is running, pid: ${pid//$'\n'/, }"
    else
        echo_red "[$name] is not running"
        [[ $3 == "CRITICAL" ]] && RC=1
    fi
}

function check_seahub_running () {
    # if pid=$(pgrep -f "/seahub/manage.py" 2>/dev/null 1>&2 || pgrep -f "seahub.wsgi:application" 2>/dev/null 1>&2); then
    if pid=$(pgrep -f "/seahub/manage.py" 2>/dev/null || pgrep -f "seahub.wsgi:application" 2>/dev/null); then
        echo "[seahub] is running, pid: ${pid//$'\n'/, }"
    else
        echo_red "[seahub] is not runnig"
        [[ $1 == "CRITICAL" ]] && RC=1
    fi
}

function keeper_archiving_status () {
    ${seafile_dir}/scripts/run_keeper_script.sh ${script_path}/pro/pro.py archive -ls
    echo "Note: use ${script_path}/pro/pro.py archive [command] for more archiving actions"
}

function check_and_exit_keeper_archiving_running () {
    result=$(${seafile_dir}/scripts/run_keeper_script.sh ${script_path}/pro/pro.py archive --is-processing)
    if [ "$result" != "false" ]; then
        echo_red "Cannot stop, archiving is currently running."
        keeper_archiving_status
        exit 1
    fi
}



#echo -e "\n \n About to perform $1 for seafile at `date -Iseconds` \n " >> ${seafile_init_log}
#echo -e "\n \n About to perform $1 for seahub at `date -Iseconds` \n " >> ${seahub_init_log}


echo "Keeper ${__NODE_TYPE__} node ${__NODE_FQDN__}, cmd: $1"

case "$1" in
        start|restart)
            if [ "$1" == "restart" ]; then
                echo "Restarting..."
            else
                echo "Starting..."
            fi

            pushd ${seafile_dir} >/dev/null

	    if [ ${__OFFICE_CONVERTER_ENABLED__} == "true" ] && [ ! -d ${__OFFICE_CONVERTER_OUTPUTDIR__} ]
	    then
		    mkdir -p ${__OFFICE_CONVERTER_OUTPUTDIR__} && chown -R ${user}.${group} ${__OFFICE_CONVERTER_OUTPUTDIR__}
	    fi

            if [ ${__NODE_TYPE__} == "APP" ]; then
                ${USR_CTX} ${script_path}/seafile.sh ${1} >> ${seafile_init_log}
                ${USR_CTX} ${script_path}/seahub.sh ${1} >> ${seahub_init_log}
                ${ROOT_CTX} ${seafile_dir}/scripts/catalog-service.sh ${1}
                systemctl ${1} ${WEB_SERVER}.service
            elif [ ${__NODE_TYPE__} == "BACKGROUND" ]; then
                if [ "$1" == "restart" ]; then
                    $0 stop $2
                    sleep 3
                    echo "Starting..."
                fi
                ${USR_CTX} ${script_path}/seafile.sh ${1} >> ${seafile_init_log}
                ${USR_CTX} ${script_path}/seahub.sh ${1} >> ${seahub_init_log}
                ${USR_CTX} ${seafile_dir}/scripts/keeper-background-tasks.sh ${1} >> ${background_init_log}
            elif [ ${__NODE_TYPE__} == "SINGLE" ]; then
                if [ "$1" == "restart" ]; then
                    $0 stop $2
                    sleep 3
                    echo "Starting..."
                fi
                ${USR_CTX} ${script_path}/seafile.sh ${1} >> ${seafile_init_log}
                ${USR_CTX} ${script_path}/seahub.sh ${1} >> ${seahub_init_log}
                ${USR_CTX} ${seafile_dir}/scripts/keeper-background-tasks.sh ${1} >> ${background_init_log}
                ${ROOT_CTX} ${seafile_dir}/scripts/catalog-service.sh ${1} 
            fi
            sleep 3
            echo "Done"
            $0 status
        ;;
        stop)
            echo "Stopping..."
            if [ ${__NODE_TYPE__} == "APP" ]; then
                ${USR_CTX} ${script_path}/seahub.sh stop >> ${seahub_init_log}
                ${USR_CTX} ${script_path}/seafile.sh stop >> ${seafile_init_log}
                ${ROOT_CTX} ${seafile_dir}/scripts/catalog-service.sh stop 
            elif [ ${__NODE_TYPE__} == "BACKGROUND" ]; then
                if [ "$2" != "--force" ]; then
                    check_and_exit_keeper_archiving_running
                fi
                ${USR_CTX} ${seafile_dir}/scripts/keeper-background-tasks.sh stop >> ${background_init_log}
                ${USR_CTX} ${script_path}/seahub.sh stop >> ${seahub_init_log}
                ${USR_CTX} ${script_path}/seafile.sh stop >> ${seafile_init_log}
            elif [ ${__NODE_TYPE__} == "SINGLE" ]; then
                if [ "$2" != "--force" ]; then
                    check_and_exit_keeper_archiving_running
                fi
                ${USR_CTX} ${seafile_dir}/scripts/keeper-background-tasks.sh stop >> ${background_init_log}
                ${USR_CTX} ${script_path}/seahub.sh stop >> ${seahub_init_log}
                ${USR_CTX} ${script_path}/seafile.sh stop >> ${seafile_init_log}
                ${ROOT_CTX} ${seafile_dir}/scripts/catalog-service.sh stop
            fi
            sleep 3
            echo "Done"
            #systemctl ${1} memcached.service
        ;;
        archiving-status)
        keeper_archiving_status
        ;;
        archiving-kill)
            keeper_archiving_kill
        ;;
        cluster-restart|cluster-status)
            nodes=($(echo ${__CLUSTER_NODES__}))
            for i in "${nodes[@]}"; do
                ssh ${i} "keeper-service ${1#cluster-}"
            done
        ;;
        restart-gpfs)
            restart_gpfs
        ;;
        switch-maintenance-mode)
            check_en_dis_nginx
            switch_maintenance_mode
        ;;
        status)
            RC=0
            check_puppet
            if [ ${__NODE_TYPE__} != "BACKGROUND" ] ; then
                check_mysql
            fi
            check_component_running "seafile-controller" "seafile-controller -c ${default_ccnet_conf_dir}" "CRITICAL"
            check_seahub_running "CRITICAL"
            check_component_running "ccnet-server" "ccnet-server.*-c ${default_ccnet_conf_dir}" "CRITICAL"
            check_component_running "seaf-server" "seaf-server.*-c ${default_ccnet_conf_dir}" "CRITICAL"
            check_component_running "seafevents" "seafevents.main" "CRITICAL"
            if [ ${__NODE_TYPE__} == "BACKGROUND" ] || [ ${__NODE_TYPE__} == "SINGLE" ] ; then
                check_component_running "background_task" "seafevents.background_task" "CRITICAL"
                check_component_running "keeper_archiving" "archiving_server.py" "CRITICAL"
            fi    
            if [ ${__NODE_TYPE__} != "BACKGROUND" ] ; then
                check_keepalived
                check_component_running "keeper-catalog" "uwsgi.*catalog.ini"  "CRITICAL"
            fi
            check_memcached
            #check_component_running "memcached" "memcached" "CRITICAL"
            [ $RC -eq 0 ] && echo_green "Status is OK" || echo_red "Status is not OK" 
            exit $RC
        ;;
        *)
            echo "Usage: ./$(basename $(readlink -f $0)) {start|stop[ --force]|restart[ --force]|status|restart-gpfs|switch-maintenance-mode|archiving-status}"
            exit 1
        ;;
esac

