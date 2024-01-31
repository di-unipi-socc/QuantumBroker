#!/bin/bash

apt update
apt install -y python3-pip
apt install -y python3-venv

virtualenv -p python3 venv
source venv/bin/activate

apt install -y gringo
apt install -y awscli

pip3 install --no-deps -r requirements.txt