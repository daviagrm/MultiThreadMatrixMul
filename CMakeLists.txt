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

# Versao CUDA: so e compilada se houver um compilador CUDA (nvcc) instalado,
# para que as outras versoes continuem compilando em maquinas sem GPU NVIDIA.
include(CheckLanguage)
check_language(CUDA)
if(CMAKE_CUDA_COMPILER)
    enable_language(CUDA)
    add_executable(cuda cuda.cu)
    # "native" (CMake 3.24+) gera codigo para a GPU desta maquina
    if(CMAKE_VERSION VERSION_GREATER_EQUAL 3.24)
        set_target_properties(cuda PROPERTIES CUDA_ARCHITECTURES native)
    endif()
else()
    message(STATUS "Compilador CUDA nao encontrado: o executavel 'cuda' nao sera gerado")
endif()

# Versao OpenCL: roda em GPUs AMD, NVIDIA e Intel. So e compilada se os
# cabecalhos e a biblioteca do OpenCL forem encontrados.
find_package(OpenCL QUIET)
if(OpenCL_FOUND)
    add_executable(opencl opencl.c)
    target_link_libraries(opencl PRIVATE OpenCL::OpenCL)
else()
    message(STATUS "OpenCL nao encontrado: o executavel 'opencl' nao sera gerado")
endif()
