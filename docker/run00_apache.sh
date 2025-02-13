#!/bin/bash

#_ROSMASTER=${1:-"http://localhost:11311"}

script_dir=$(cd $(dirname ${BASH_SOURCE:-$0}); pwd)

trap "echo HUP; docker kill apache_rosbridge; exit 0" SIGHUP
trap "echo INT; docker kill apache_rosbridge; exit 0" SIGINT

${script_dir}/irsl_docker_irsl_system/run.sh -w $(pwd)/userdir --name apache_rosbridge \
             --mount "-v $(pwd)/../html:/var/www/html" \
             --mount "-v $(pwd)/userdir/server.key:/irsl_security/server.key" \
             --mount "-v $(pwd)/userdir/server.crt:/irsl_security/server.crt" \
             --mount "-v $(pwd)/sites-available:/etc/apache2/sites-available" \
             --image apache_rosbridge:noetic /userdir/run_apache.sh &
wait
