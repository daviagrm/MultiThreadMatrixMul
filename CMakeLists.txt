cmake_minimum_required(VERSION 3.10)
project(MultiThreadMatrixMul C)

set(CMAKE_C_STANDARD 11)

find_package(Threads REQUIRED)

add_executable(sequencial sequencial.c)

add_executable(paralelo main.c)
target_link_libraries(paralelo PRIVATE Threads::Threads)

find_package(OpenMP REQUIRED)

add_executable(openmp openmp.c)
target_link_libraries(openmp PRIVATE OpenMP::OpenMP_C)
