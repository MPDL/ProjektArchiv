#!/bin/bash

### KEEPER COMMON Utils

function echo_green () {
    if [ "$(tput colors 2>/dev/null)" ]; then 
        echo -e "$(tput setaf 2)${1}$(tput sgr0)"
    else
        echo -e "${1}"
    fi
}

function echo_red () {
    if [ "$(tput colors 2>/dev/null)" ]; then 
        echo -e "$(tput setaf 1)${1}$(tput sgr0)"
    else
        echo -e "${1}"
    fi
}

function err_and_exit () {
	if [ "$1" ]; then
        echo_red "Error: $1"
		# TODO: send notification 
	fi
	exit 1;
}

function up_err_and_exit () {
	startup_seafile
	err_and_exit "$1"
}



function check_file () {
    if [ ! -f "$1" ]; then
		if [ -n "$2" ]; then
			err_and_exit "$2"
		fi
        err_and_exit "Cannot find file $1"
    fi
}

### INJECT KEEPER PROPERTIES

SEAFILE_DIR=/opt/seafile
### GET INSTANCE PROPERTIES FILE
# KEEPER instance properties file should be located in SEAFILE_DIR!!!
FILES=( $(find ${SEAFILE_DIR} -maxdepth 1 -type f -name "keeper*.properties") )
( [[ $? -ne 0 ]] || [[ ${#FILES[@]} -eq 0 ]] ) && err_and_exit "Cannot find instance properties file in ${SEAFILE_DIR}"
[[ ${#FILES[@]} -ne 1 ]] && err_and_exit "Too many instance properties files in ${SEAFILE_DIR}:\n ${FILES[*]}"
PROPERTIES_FILE="${FILES[0]}"
source "${PROPERTIES_FILE}"
if [ $? -ne 0  ]; then
	err_and_exit "Cannot intitialize variables"
fi
### END


