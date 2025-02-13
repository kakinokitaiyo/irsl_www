#!/bin/bash

_COMMON_NAME=${1:-"eiiris.tut.ac.jp"}

if [ ! -e userdir/server.key ]; then
    openssl genrsa -out userdir/server.key 2048
fi

if [ ! -e userdir/server.crt ]; then
    openssl req -out userdir/server.csr -key userdir/server.key -new -subj "/C=JP/ST=Aichi/O=IRSL/CN=${_COMMON_NAME}"
    openssl x509 -req -days 3650 -signkey userdir/server.key -in userdir/server.csr -out userdir/server.crt
fi

docker build . --pull -f Dockerfile.apache_rosbridge --build-arg BASE_IMAGE=ros:noetic-ros-base -t apache_rosbridge:noetic
