#!/bin/bash

_COMMON_NAME=${1:-"eiiris.tut.ac.jp"}

docker build . --pull -f Dockerfile.apache_rosbridge --build-arg BASE_IMAGE=ros:noetic-ros-base -t temp_build:apache0

docker build .        -f Dockerfile.add_files -t apache_rosbridge_win:noetic \
       --build-arg BASE_IMAGE=temp_build:apache0 \
       --build-arg COMMON_NAME=${_COMMON_NAME}
