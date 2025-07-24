cmake_minimum_required(VERSION 3.0.2)
project(irsl_www)

find_package(catkin REQUIRED
)

message("build_local: $ENV{IRSL_BUILD_LOCAL}")
if ("$ENV{IRSL_BUILD_LOCAL}")
  message("build_mode: BUILD_LOCAL")
else()
  message("build_mode: JUST_INSTALL_FILES")
endif()

###################################
## catkin specific configuration ##
###################################
## The catkin_package macro generates cmake config files for your package
## Declare things to be passed to dependent projects
## INCLUDE_DIRS: uncomment this if your package contains header files
## LIBRARIES: libraries you create in this project that dependent projects also need
## CATKIN_DEPENDS: catkin_packages dependent projects also need
## DEPENDS: system dependencies of this project that dependent projects also need
catkin_package(
#  INCLUDE_DIRS include
#  LIBRARIES irsl_docker_pkg_sample
#  CATKIN_DEPENDS irsl_detection_msgs irsl_detection_srvs rospy sensor_msgs std_msgs
#  DEPENDS system_lib
)

#############
## Install ##
#############

# all install targets should use catkin DESTINATION variables
# See http://ros.org/doc/api/catkin/html/adv_user_guide/variables.html

## Mark cpp header files for installation
# install(DIRECTORY include/${PROJECT_NAME}/
#   DESTINATION ${CATKIN_PACKAGE_INCLUDE_DESTINATION}
#   FILES_MATCHING PATTERN "*.h"
#   PATTERN ".svn" EXCLUDE
# )

## Mark other files for installation (e.g. launch and bag files, etc.)

install(DIRECTORY docker
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
  FILES_MATCHING
    PATTERN "*.yaml"
    PATTERN "*.sh" PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE
)
install(DIRECTORY docker/userdir
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/docker
  FILES_MATCHING
    PATTERN "*"
    PATTERN "*.sh" PERMISSIONS OWNER_READ OWNER_WRITE OWNER_EXECUTE GROUP_READ GROUP_EXECUTE WORLD_READ WORLD_EXECUTE
)
install(DIRECTORY
  docker/sites-available
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}/docker
)
install(DIRECTORY
  html
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
)
