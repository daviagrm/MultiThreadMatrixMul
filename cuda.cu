#include <stdio.h>
#include <stdlib.h>
#include <cuda_runtime.h>

//Verifica o retorno de cada chamada CUDA e encerra com a mensagem de erro.
#define CUDA_OK(chamada)                                                   \
    do {                                                                   \
        cudaError_t erro = (chamada);                                      \
        if (erro != cudaSuccess) {                                         \
            fprintf(stderr, "Erro CUDA em %s:%d: %s\n", __FILE__, __LINE__, \
                    cudaGetErrorString(erro));                             \
            exit(1);                                                       \
        }                                                                  \
    } while (0)

//Cada thread da GPU calcula UM elemento de prod: prod[lin][col].
//As threads sao organizadas em blocos 2D de lado x lado, e os blocos numa
//grade 2D que cobre a matriz inteira. O indice x (colunas) varia mais
//rapido dentro de um warp, entao threads vizinhas leem posicoes vizinhas
//de m2 e escrevem posicoes vizinhas de prod (acesso "coalescido").
//Como cada thread escreve uma posicao diferente, nao ha condicao de corrida.
__global__ void multiplica(const int *m1, const int *m2, int *prod, int tam) {
    int lin = blockIdx.y * blockDim.y + threadIdx.y;
    int col = blockIdx.x * blockDim.x + threadIdx.x;

    //a grade pode passar do tamanho da matriz quando tam nao e multiplo
    //do lado do bloco; essas threads extras nao fazem nada
    if (lin < tam && col < tam) {
        int acumulador = 0;
        for (int x = 0; x < tam; x++) {
            acumulador += m1[lin * tam + x] * m2[x * tam + col];
        }
        prod[lin * tam + col] = acumulador;
    }
}

int main(int argc, char* argv[]) {
    int tam = 1000;
    int lado = 16;
    long long soma = 0;
    int i, j;

    //linha de comando: ./cuda [tamanho] [lado do bloco]
    //  tamanho >= 1   lado: 8 | 16 | 32 (blocos de 64, 256 ou 1024 threads)
    if (argc > 1) {
        tam = atoi(argv[1]);
    }
    if (argc > 2) {
        lado = atoi(argv[2]);
    }
    if (tam < 1 || (lado != 8 && lado != 16 && lado != 32) || argc > 3) {
        fprintf(stderr, "Uso: %s [tamanho >= 1] [8|16|32]\n", argv[0]);
        return 1;
    }

    size_t bytes = (size_t) tam * tam * sizeof(int);

    //matrizes na memoria principal (CPU), inicializadas como nas outras versoes
    int *m1 = (int *) malloc(bytes);
    int *m2 = (int *) malloc(bytes);
    int *prod = (int *) malloc(bytes);
    if (m1 == NULL || m2 == NULL || prod == NULL) {
        fprintf(stderr, "Falha ao alocar as matrizes\n");
        return 1;
    }
    for (i = 0; i < tam; i++) {
        for (j = 0; j < tam; j++) {
            m1[i * tam + j] = i;
            m2[i * tam + j] = 2;
            prod[i * tam + j] = 0;
        }
    }

    //matrizes na memoria da GPU (a GPU nao enxerga a memoria da CPU)
    int *d_m1, *d_m2, *d_prod;
    CUDA_OK(cudaMalloc((void **) &d_m1, bytes));
    CUDA_OK(cudaMalloc((void **) &d_m2, bytes));
    CUDA_OK(cudaMalloc((void **) &d_prod, bytes));

    dim3 bloco(lado, lado);
    dim3 grade((tam + lado - 1) / lado, (tam + lado - 1) / lado);

    //Aquecimento: a primeira chamada de um kernel carrega o codigo na GPU,
    //o que leva alguns milissegundos. Isso acontece uma vez por programa
    //(como carregar o executavel), entao fica fora da medicao. As entradas
    //sao zeradas so para o kernel nao ler memoria sem valor definido; o
    //resultado do aquecimento e sobrescrito depois.
    CUDA_OK(cudaMemset(d_m1, 0, bytes));
    CUDA_OK(cudaMemset(d_m2, 0, bytes));
    multiplica<<<grade, bloco>>>(d_m1, d_m2, d_prod, tam);
    CUDA_OK(cudaGetLastError());
    CUDA_OK(cudaDeviceSynchronize());

    //Tempo medido com eventos da GPU, que marcam o instante em que cada
    //etapa termina na propria GPU.
    cudaEvent_t ini, ini_kernel, fim_kernel, fim;
    CUDA_OK(cudaEventCreate(&ini));
    CUDA_OK(cudaEventCreate(&ini_kernel));
    CUDA_OK(cudaEventCreate(&fim_kernel));
    CUDA_OK(cudaEventCreate(&fim));

    CUDA_OK(cudaEventRecord(ini));

    //1. copia as entradas da CPU para a GPU
    CUDA_OK(cudaMemcpy(d_m1, m1, bytes, cudaMemcpyHostToDevice));
    CUDA_OK(cudaMemcpy(d_m2, m2, bytes, cudaMemcpyHostToDevice));

    //2. multiplicacao: tam x tam threads, uma por elemento de prod
    CUDA_OK(cudaEventRecord(ini_kernel));
    multiplica<<<grade, bloco>>>(d_m1, d_m2, d_prod, tam);
    CUDA_OK(cudaGetLastError());
    CUDA_OK(cudaEventRecord(fim_kernel));

    //3. copia o resultado da GPU de volta para a CPU
    CUDA_OK(cudaMemcpy(prod, d_prod, bytes, cudaMemcpyDeviceToHost));

    CUDA_OK(cudaEventRecord(fim));
    CUDA_OK(cudaEventSynchronize(fim));

    float total_ms, kernel_ms;
    CUDA_OK(cudaEventElapsedTime(&total_ms, ini, fim));
    CUDA_OK(cudaEventElapsedTime(&kernel_ms, ini_kernel, fim_kernel));

    cudaDeviceProp prop;
    CUDA_OK(cudaGetDeviceProperties(&prop, 0));

    printf("Versao CUDA | matriz %dx%d | blocos de %dx%d threads | grade de %dx%d blocos\n",
           tam, tam, lado, lado, grade.x, grade.y);
    printf("GPU: %s\n", prop.name);
    //"Tempo transcorrido" inclui as copias, para comparar com as versoes de
    //CPU, que ja tem os dados na memoria principal.
    printf("Tempo transcorrido: %ld us (%.3f ms)\n",
           (long) (total_ms * 1000 + 0.5f), total_ms);
    printf("Tempo do kernel: %ld us (%.3f ms)\n",
           (long) (kernel_ms * 1000 + 0.5f), kernel_ms);

    //soma de verificacao: deve ser igual nas outras versoes
    for (i = 0; i < tam; i++)
        for (j = 0; j < tam; j++)
            soma += prod[i * tam + j];
    printf("Soma de verificacao: %lld\n", soma);

    //imprimindo resultado (apenas matrizes pequenas)
    if (tam == 10) {
        for (i = 0; i < tam; i++) {
            for (j = 0; j < tam; j++) {
                printf("%d ", prod[i * tam + j]);
            }
            printf("\n");
        }
    }

    cudaEventDestroy(ini);
    cudaEventDestroy(ini_kernel);
    cudaEventDestroy(fim_kernel);
    cudaEventDestroy(fim);
    cudaFree(d_m1);
    cudaFree(d_m2);
    cudaFree(d_prod);
    free(m1);
    free(m2);
    free(prod);
    return 0;
}
