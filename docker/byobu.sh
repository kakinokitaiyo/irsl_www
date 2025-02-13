#!/bin/bash

script_dir=$(cd $(dirname ${BASH_SOURCE:-$0}); pwd)

##
SESSION_NAME=apache_rosbridge
##
DEFAULT_NAME=org

## 新たなセッションを始める
byobu-tmux new-session -d -s $SESSION_NAME -n $DEFAULT_NAME

WINDOW_NAME=w0

COMMAND="${script_dir}/run00_apache.sh"
byobu-tmux new-window -t $SESSION_NAME -k -n $WINDOW_NAME
byobu-tmux send-keys  -t $SESSION_NAME:$WINDOW_NAME "$COMMAND" C-m # TODO : space
# byobu-tmux select-window -t 0

sleep 1;

WINDOW_NAME=w1

MASTER=http://cpshost.irsl.eiiris.tut.ac.jp:11211
HOST=cpshost.irsl.eiiris.tut.ac.jp
PORT=8900

COMMAND="${script_dir}/run01_rosbridge.sh ${MASTER} ${HOST} ${PORT}"
byobu-tmux new-window -t $SESSION_NAME -k -n $WINDOW_NAME
byobu-tmux send-keys  -t $SESSION_NAME:$WINDOW_NAME "$COMMAND" C-m # TODO : space
# byobu-tmux select-window -t 0
