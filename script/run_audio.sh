#!/bin/bash

source /opt/ros/noetic/setup.bash
export ROS_HOSTNAME=133.15.97.61
export ROS_IP=133.15.97.61
export ROS_MASTER_URI=http://133.15.97.68:11311

python3 /userdir/sub_audio.py

## docker exec -it docker-bridge-1 bash /userdir/run_audio.sh
