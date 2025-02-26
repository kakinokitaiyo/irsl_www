#!/bin/bash

_COMMON_NAME=${COMMON_NAME:-"eiiris.tut.ac.jp"}
_BASE_IMAGE=${1:-"ros:noetic-ros-base"}
_OUTPUT_IMAGE=${OUTPUT:-"apache_rosbridge_win:noetic"}

echo "docker build . --no-cache --pull -f Dockerfile.apache_rosbridge --build-arg BASE_IMAGE=${_BASE_IMAGE} -t temp_build:apache0"
docker build . --no-cache --pull -f Dockerfile.apache_rosbridge --build-arg BASE_IMAGE=${_BASE_IMAGE} -t temp_build:apache0

docker build ..       -f Dockerfile.add_files -t  ${_OUTPUT_IMAGE} \
       --build-arg BASE_IMAGE=temp_build:apache0 \
       --build-arg COMMON_NAME=${_COMMON_NAME}
