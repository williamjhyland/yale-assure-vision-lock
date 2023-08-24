#!/bin/bash

# Grab directory
current_dir=${PWD}
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# install pip
sudo apt install python3-pip

# Create environment
python3.9 -m venv ${SCRIPT_DIR}

# Activate environment
source ${SCRIPT_DIR}/bin/activate

# Install requirements
pip install -r ./requirements.txt

# Deactivate environment
deactivate