project(WR CXX)

set(application_core_name "${PROJECT_NAME}Core")
set(application_name "${PROJECT_NAME}App")

# Core library
file(GLOB_RECURSE application_core_sources
     ${application_name}.cpp
     ${application_name}_variables.cpp
     packages/*.cpp)

if (${KRATOS_BUILD_TESTING} MATCHES ON)
    file(GLOB_RECURSE application_test_sources
         packages/*/test/*.cpp)
endif()

add_library(${application_core_name} SHARED ${application_core_sources} ${application_test_sources})
target_link_libraries(${application_core_name} PUBLIC KratosCore)
target_include_directories(${application_core_name} PUBLIC
                           "${KRATOS_SOURCE_DIR}/kratos"
                           "${CMAKE_CURRENT_SOURCE_DIR}/include"
                           "${CMAKE_CURRENT_SOURCE_DIR}/packages")
set_target_properties(${application_core_name} PROPERTIES COMPILE_DEFINITIONS "${PROJECT_NAME}_APPLICATION=EXPORT,API")

# Python bindings
file(GLOB_RECURSE application_python_interface_sources python_bindings/*.cpp)
pybind11_add_module(${application_name} MODULE THIN_LTO ${application_python_interface_sources})
target_link_libraries(${application_name} PRIVATE ${application_core_name})
set_target_properties(${application_name} PROPERTIES PREFIX "")

if(${CMAKE_SYSTEM_NAME} MATCHES "Windows")
    set_target_properties(${application_name} PROPERTIES SUFFIX .pyd) # Suffix on Windows
elseif(${CMAKE_SYSTEM_NAME} MATCHES "Darwin")
    set_target_properties(${application_name} PROPERTIES SUFFIX .so) # Suffix on MacOS
endif()

include(pybind11Tools)
kratos_python_install(${INSTALL_PYTHON_USING_LINKS} "${CMAKE_CURRENT_SOURCE_DIR}/python_scripts" KratosMultiphysics/${application_name})

if (${INSTALL_TESTING_FILES} MATCHES ON)
    install(DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}/tests" DESTINATION applications/${application_name}
            PATTERN "*.git" EXCLUDE
            PATTERN "*.c" EXCLUDE
            PATTERN "*.h" EXCLUDE
            PATTERN "*.cpp" EXCLUDE
            PATTERN "*.hpp" EXCLUDE)
endif()

# Install targets
install(TARGETS ${application_core_name} DESTINATION libs)
install(TARGETS ${application_name} DESTINATION libs)

# Define custom targets
set(KRATOS_KERNEL "${KRATOS_KERNEL};${application_core_name}" PARENT_SCOPE)
set(KRATOS_PYTHON_INTERFACE "${KRATOS_PYTHON_INTERFACE};${application_name}" PARENT_SCOPE)
