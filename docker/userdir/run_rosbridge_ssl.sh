#!/bin/bash

_ROSMASTER=${1:-"http://localhost:11311"}
_ADDRESS=${2:-simserver.irsl.eiiris.tut.ac.jp}
_PORT=${3:-9990}

unset ROS_IP
export ROS_HOSTNAME=${_ADDRESS}
export ROS_MASTER_URI=${_ROSMASTER}

roslaunch rosbridge_server rosbridge_websocket.launch \
          address:=${_ADDRESS} port:=${_PORT} ssl:=true \
          certfile:=/irsl_security/server.crt \
          keyfile:=/irsl_security/server.key
