#!/bin/bash

_ROSMASTER=${1:-"http://localhost:11311"}
_ADDRESS=${2:-simserver.irsl.eiiris.tut.ac.jp}
_PORT=${3:-9990}

script_dir=$(cd $(dirname ${BASH_SOURCE:-$0}); pwd)

function kill_launched() {
    pid=$(./irsl_docker_irsl_system/exec.sh --name apache_rosbridge -- pgrep -f 'roslaunch rosbridge_server rosbridge_websocket')
    if [ -n "$pid" ]; then
        echo "PID: $pid"
        ./irsl_docker_irsl_system/exec.sh --name apache_rosbridge -- kill -INT "$pid"
    fi
}

trap "echo HUP; trap - SIGINT; kill_launched; exit 0" SIGHUP
trap "echo INT; trap - SIGINT; kill_launched; exit 0" SIGINT
#trap "echo TERM && trap - SIGINT && kill_launched && kill -INT -- -$$" SIGTERM
#trap "echo EXIT && trap - SIGINT && kill_launched && kill -INT -- -$$" EXIT

# irsl_docker_irsl_system/exec.sh --name apache_rosbridge /userdir/run_rosbridge.sh &
${script_dir}/irsl_docker_irsl_system/exec.sh --name apache_rosbridge /userdir/run_video_server.sh ${_ROSMASTER} ${_ADDRESS} ${_PORT} &

wait
