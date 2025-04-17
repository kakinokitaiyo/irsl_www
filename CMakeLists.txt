cmake_minimum_required(VERSION 3.0.2)

project(irsl_mobile_arm)

find_package(catkin REQUIRED)

catkin_package()

install(DIRECTORY script
  DESTINATION ${CATKIN_PACKAGE_SHARE_DESTINATION}
  USE_SOURCE_PERMISSIONS
  )
