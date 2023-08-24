#!/bin/bash

# Grab directory
current_dir=${PWD}
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd `dirname $0`

# Be sure to use `exec` so that termination signals reach the python process,
# or handle forwarding termination signals manually

# setup our python virtual environment
source ${SCRIPT_DIR}/bin/activate

python ${SCRIPT_DIR}/src/main.py $@

# deactivate - if we get here
deactivate