#!/bin/bash

_ROSMASTER=${1:-"http://localhost:11311"}
_ADDRESS=${2:-simserver.irsl.eiiris.tut.ac.jp}
_PORT=${3:-9990}

unset ROS_IP
export ROS_HOSTNAME=${_ADDRESS}
export ROS_MASTER_URI=${_ROSMASTER}

roslaunch /userdir/web_video_server.launch address:=${_ADDRESS} port:=${_PORT}
