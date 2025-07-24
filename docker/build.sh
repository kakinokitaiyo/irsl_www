#!/bin/bash

abs_dir=$(dirname "$(readlink -f "$0")")

_COMMON_NAME="eiiris.tut.ac.jp"

_REPO="repo.irsl.eiiris.tut.ac.jp/"
_TAG="noetic"
_KEYS=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --common-name)
            _COMMON_NAME="$2"
            shift
            shift
            ;;
        --repo)
            _REPO="$2"
            shift
            shift
            ;;
        --tag)
            _TAG="$2"
            shift
            shift
            ;;
        --just-keys)
            _KEYS="yes"
            shift
            ;;
        --help)
            echo "Usage: build.sh [--common-name COMMON_NAME] [--repo REPO] [--tag TAG] [--just-keys]"
            echo ""
            echo "Options:"
            echo "  --common-name COMMON_NAME   Set the common name for SSL certificate generation (default: eiiris.tut.ac.jp)."
            echo "  --repo REPO                 Specify the Docker repository (default: repo.irsl.eiiris.tut.ac.jp/)."
            echo "  --tag TAG                   Specify the Docker image tag (default: noetic)."
            echo "  --just-keys                 Only generate SSL keys and exit."
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

if [ ! -e ${abs_dir}/userdir/server.key ]; then
    openssl genrsa -out ${abs_dir}/userdir/server.key 2048
fi

if [ ! -e ${abs_dir}/userdir/server.crt ]; then
    openssl req -out ${abs_dir}/userdir/server.csr -key ${abs_dir}/userdir/server.key -new -subj "/C=JP/ST=Aichi/O=IRSL/CN=${_COMMON_NAME}"
    openssl x509 -req -days 3650 -signkey ${abs_dir}/userdir/server.key -in ${abs_dir}/userdir/server.csr -out ${abs_dir}/userdir/server.crt
fi

if [ -n "${_KEYS}" ]; then
    exit 0
fi

if   [ "${_TAG}" == "noetic" ]; then
(cd ${abs_dir}; \
docker build . --pull -f Dockerfile.apache_rosbridge --build-arg BASE_IMAGE=ros:noetic-ros-base -t ${_REPO}apache_rosbridge:noetic ; )
elif [ "${_TAG}" == "one"    ]; then
(cd ${abs_dir}; \
docker build . --pull -f Dockerfile.apache_rosbridge --build-arg BASE_IMAGE=${_REPO}irsl_base:one_opengl -t ${_REPO}apache_rosbridge:one ; )
fi
