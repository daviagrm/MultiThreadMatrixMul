//Versao em GPU com OpenCL. Diferente do CUDA (so NVIDIA), o OpenCL roda em
//GPUs de qualquer fabricante: AMD, NVIDIA e Intel. O codigo que executa na
//GPU (o kernel) fica num texto e e compilado pelo driver na hora.
#define CL_TARGET_OPENCL_VERSION 120

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef __APPLE__
#include <OpenCL/opencl.h>
#else
#include <CL/cl.h>
#endif

#define MAX_GPUS 16

//Verifica o retorno de cada chamada OpenCL e encerra com o codigo de erro.
//(Os codigos estao em CL/cl.h; por exemplo, -5 = falta de recursos.)
#define CL_OK(chamada)                                                    \
    do {                                                                  \
        cl_int erro_ = (chamada);                                         \
        if (erro_ != CL_SUCCESS) {                                        \
            fprintf(stderr, "Erro OpenCL %d em %s:%d\n", (int) erro_,      \
                    __FILE__, __LINE__);                                  \
            exit(1);                                                      \
        }                                                                 \
    } while (0)

//Kernel: igual ao da versao CUDA. Cada item de trabalho (thread da GPU)
//calcula UM elemento de prod. A dimensao 0 (colunas) varia mais rapido,
//entao itens vizinhos leem posicoes vizinhas de m2 e escrevem posicoes
//vizinhas de prod.
static const char *FONTE_KERNEL =
    "__kernel void multiplica(__global const int *m1,\n"
    "                         __global const int *m2,\n"
    "                         __global int *prod, int tam) {\n"
    "    int col = get_global_id(0);\n"
    "    int lin = get_global_id(1);\n"
    "    if (lin < tam && col < tam) {\n"
    "        int acumulador = 0;\n"
    "        for (int x = 0; x < tam; x++) {\n"
    "            acumulador += m1[lin * tam + x] * m2[x * tam + col];\n"
    "        }\n"
    "        prod[lin * tam + col] = acumulador;\n"
    "    }\n"
    "}\n";

//Procura as GPUs de todas as plataformas (cada fabricante instala a sua).
static int lista_gpus(cl_device_id *gpus, cl_platform_id *plats) {
    cl_platform_id plataformas[8];
    cl_uint n_plat = 0;
    int n = 0;
    if (clGetPlatformIDs(8, plataformas, &n_plat) != CL_SUCCESS) {
        return 0;
    }
    for (cl_uint p = 0; p < n_plat && n < MAX_GPUS; p++) {
        cl_uint n_dev = 0;
        if (clGetDeviceIDs(plataformas[p], CL_DEVICE_TYPE_GPU, MAX_GPUS - n,
                           gpus + n, &n_dev) != CL_SUCCESS) {
            continue;   //plataforma sem GPU (por exemplo, so CPU)
        }
        for (cl_uint d = 0; d < n_dev; d++) {
            plats[n + d] = plataformas[p];
        }
        n += (int) n_dev;
    }
    return n;
}

static void nome_gpu(cl_device_id gpu, cl_platform_id plat, char *saida, size_t tam_saida) {
    char dev[256] = "?", pla[256] = "?";
    clGetDeviceInfo(gpu, CL_DEVICE_NAME, sizeof dev, dev, NULL);
    clGetPlatformInfo(plat, CL_PLATFORM_NAME, sizeof pla, pla, NULL);
    snprintf(saida, tam_saida, "%s (%s)", dev, pla);
}

//Duracao de um comando, em nanossegundos, pelos contadores da propria GPU.
static cl_ulong instante(cl_event ev, cl_profiling_info qual) {
    cl_ulong t = 0;
    CL_OK(clGetEventProfilingInfo(ev, qual, sizeof t, &t, NULL));
    return t;
}

int main(int argc, char *argv[]) {
    cl_device_id gpus[MAX_GPUS];
    cl_platform_id plats[MAX_GPUS];
    char nome[600];
    int n_gpus = lista_gpus(gpus, plats);

    //./opencl --listar  mostra as GPUs encontradas e seus indices
    if (argc == 2 && strcmp(argv[1], "--listar") == 0) {
        for (int g = 0; g < n_gpus; g++) {
            nome_gpu(gpus[g], plats[g], nome, sizeof nome);
            printf("%d: %s\n", g, nome);
        }
        return n_gpus > 0 ? 0 : 1;
    }

    //linha de comando: ./opencl [tamanho] [lado do bloco] [gpu]
    //  tamanho >= 1   lado: 8 | 16 | 32   gpu: indice mostrado por --listar
    int tam = 1000, lado = 16, g = 0;
    if (argc > 1) tam = atoi(argv[1]);
    if (argc > 2) lado = atoi(argv[2]);
    if (argc > 3) g = atoi(argv[3]);
    if (tam < 1 || (lado != 8 && lado != 16 && lado != 32) || argc > 4) {
        fprintf(stderr, "Uso: %s [tamanho >= 1] [8|16|32] [gpu]\n"
                        "     %s --listar\n", argv[0], argv[0]);
        return 1;
    }
    if (n_gpus == 0) {
        fprintf(stderr, "Nenhuma GPU com suporte a OpenCL foi encontrada.\n"
                        "Verifique se o driver de video (AMD, NVIDIA ou Intel) esta instalado.\n");
        return 1;
    }
    if (g < 0 || g >= n_gpus) {
        fprintf(stderr, "GPU %d nao existe; use --listar para ver as %d disponiveis\n", g, n_gpus);
        return 1;
    }
    cl_device_id gpu = gpus[g];
    nome_gpu(gpu, plats[g], nome, sizeof nome);

    size_t bytes = (size_t) tam * tam * sizeof(int);
    int *m1 = malloc(bytes), *m2 = malloc(bytes), *prod = malloc(bytes);
    if (m1 == NULL || m2 == NULL || prod == NULL) {
        fprintf(stderr, "Falha ao alocar as matrizes\n");
        return 1;
    }
    //inicializando matrizes (igual as outras versoes)
    for (int i = 0; i < tam; i++) {
        for (int j = 0; j < tam; j++) {
            m1[i * tam + j] = i;
            m2[i * tam + j] = 2;
            prod[i * tam + j] = 0;
        }
    }

    //contexto e fila de comandos, com medicao de tempo ligada
    cl_int erro;
    cl_context ctx = clCreateContext(NULL, 1, &gpu, NULL, NULL, &erro);
    CL_OK(erro);
    cl_command_queue fila = clCreateCommandQueue(ctx, gpu, CL_QUEUE_PROFILING_ENABLE, &erro);
    CL_OK(erro);

    //compila o kernel para esta GPU
    cl_program prog = clCreateProgramWithSource(ctx, 1, &FONTE_KERNEL, NULL, &erro);
    CL_OK(erro);
    if (clBuildProgram(prog, 1, &gpu, "", NULL, NULL) != CL_SUCCESS) {
        char log[4096] = "";
        clGetProgramBuildInfo(prog, gpu, CL_PROGRAM_BUILD_LOG, sizeof log, log, NULL);
        fprintf(stderr, "Falha ao compilar o kernel:\n%s\n", log);
        return 1;
    }
    cl_kernel kernel = clCreateKernel(prog, "multiplica", &erro);
    CL_OK(erro);

    //algumas GPUs (varias da AMD, por exemplo) aceitam no maximo 256
    //itens por grupo; nesse caso, 32x32 = 1024 nao e possivel
    size_t max_grupo = 0;
    CL_OK(clGetKernelWorkGroupInfo(kernel, gpu, CL_KERNEL_WORK_GROUP_SIZE,
                                   sizeof max_grupo, &max_grupo, NULL));
    if ((size_t) lado * lado > max_grupo) {
        fprintf(stderr, "A GPU %s aceita no maximo %zu itens por grupo; "
                        "blocos de %dx%d nao sao possiveis\n", nome, max_grupo, lado, lado);
        return 1;
    }

    //matrizes na memoria da GPU
    cl_mem d_m1 = clCreateBuffer(ctx, CL_MEM_READ_ONLY, bytes, NULL, &erro);
    CL_OK(erro);
    cl_mem d_m2 = clCreateBuffer(ctx, CL_MEM_READ_ONLY, bytes, NULL, &erro);
    CL_OK(erro);
    cl_mem d_prod = clCreateBuffer(ctx, CL_MEM_WRITE_ONLY, bytes, NULL, &erro);
    CL_OK(erro);
    CL_OK(clSetKernelArg(kernel, 0, sizeof(cl_mem), &d_m1));
    CL_OK(clSetKernelArg(kernel, 1, sizeof(cl_mem), &d_m2));
    CL_OK(clSetKernelArg(kernel, 2, sizeof(cl_mem), &d_prod));
    CL_OK(clSetKernelArg(kernel, 3, sizeof(int), &tam));

    //No OpenCL 1.2, o total de itens precisa ser multiplo do tamanho do
    //grupo; por isso a grade e arredondada para cima (o kernel ignora o
    //que passa da matriz), como na versao CUDA.
    size_t grupo[2] = {(size_t) lado, (size_t) lado};
    size_t lados_grade = ((size_t) tam + lado - 1) / lado;
    size_t global[2] = {lados_grade * lado, lados_grade * lado};

    //Aquecimento, fora da medicao (como na versao CUDA): a primeira
    //execucao prepara o kernel na GPU. As entradas sao zeradas so para o
    //kernel nao ler memoria sem valor definido.
    int zero = 0;
    CL_OK(clEnqueueFillBuffer(fila, d_m1, &zero, sizeof zero, 0, bytes, 0, NULL, NULL));
    CL_OK(clEnqueueFillBuffer(fila, d_m2, &zero, sizeof zero, 0, bytes, 0, NULL, NULL));
    CL_OK(clEnqueueNDRangeKernel(fila, kernel, 2, NULL, global, grupo, 0, NULL, NULL));
    CL_OK(clFinish(fila));

    //1. copia as entradas para a GPU, 2. multiplica, 3. copia o resultado
    cl_event ev_m1, ev_m2, ev_kernel, ev_prod;
    CL_OK(clEnqueueWriteBuffer(fila, d_m1, CL_TRUE, 0, bytes, m1, 0, NULL, &ev_m1));
    CL_OK(clEnqueueWriteBuffer(fila, d_m2, CL_TRUE, 0, bytes, m2, 0, NULL, &ev_m2));
    CL_OK(clEnqueueNDRangeKernel(fila, kernel, 2, NULL, global, grupo, 0, NULL, &ev_kernel));
    CL_OK(clEnqueueReadBuffer(fila, d_prod, CL_TRUE, 0, bytes, prod, 0, NULL, &ev_prod));

    //tempos pelos contadores da GPU, como os eventos da versao CUDA
    double total_ms = (instante(ev_prod, CL_PROFILING_COMMAND_END)
                       - instante(ev_m1, CL_PROFILING_COMMAND_START)) / 1e6;
    double kernel_ms = (instante(ev_kernel, CL_PROFILING_COMMAND_END)
                        - instante(ev_kernel, CL_PROFILING_COMMAND_START)) / 1e6;

    printf("Versao OpenCL | matriz %dx%d | blocos de %dx%d threads | grade de %zux%zu blocos\n",
           tam, tam, lado, lado, lados_grade, lados_grade);
    printf("GPU: %s\n", nome);
    //"Tempo transcorrido" inclui as copias, como na versao CUDA
    printf("Tempo transcorrido: %ld us (%.3f ms)\n", (long) (total_ms * 1000 + 0.5), total_ms);
    printf("Tempo do kernel: %ld us (%.3f ms)\n", (long) (kernel_ms * 1000 + 0.5), kernel_ms);

    //soma de verificacao: deve ser igual nas outras versoes
    long long soma = 0;
    for (int i = 0; i < tam; i++)
        for (int j = 0; j < tam; j++)
            soma += prod[i * tam + j];
    printf("Soma de verificacao: %lld\n", soma);

    //imprimindo resultado (apenas matrizes pequenas)
    if (tam == 10) {
        for (int i = 0; i < tam; i++) {
            for (int j = 0; j < tam; j++) {
                printf("%d ", prod[i * tam + j]);
            }
            printf("\n");
        }
    }

    clReleaseEvent(ev_m1);
    clReleaseEvent(ev_m2);
    clReleaseEvent(ev_kernel);
    clReleaseEvent(ev_prod);
    clReleaseMemObject(d_m1);
    clReleaseMemObject(d_m2);
    clReleaseMemObject(d_prod);
    clReleaseKernel(kernel);
    clReleaseProgram(prog);
    clReleaseCommandQueue(fila);
    clReleaseContext(ctx);
    free(m1);
    free(m2);
    free(prod);
    return 0;
}
