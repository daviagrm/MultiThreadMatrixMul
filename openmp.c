#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <omp.h>

#define MAX_THREADS 64

//Dados: alocados em tempo de execucao, como nas outras versoes.
//Cada matriz e um vetor contiguo; o elemento [i][j] fica em [i * tam + j].
int *m1, *m2, *prod;
int tam;

int main(int argc, char* argv[]) {
    struct timeval start, end;
    long tempo_us;
    long long soma = 0;
    int num_threads = 2;
    int i, j;

    //linha de comando: ./openmp [tamanho] [threads]
    //  tamanho >= 1   threads: 1 a MAX_THREADS
    tam = 1000;
    if (argc > 1) {
        tam = atoi(argv[1]);
    }
    if (argc > 2) {
        num_threads = atoi(argv[2]);
    }
    if (tam < 1 || num_threads < 1 || num_threads > MAX_THREADS || argc > 3) {
        fprintf(stderr, "Uso: %s [tamanho >= 1] [threads: 1 a %d]\n",
                argv[0], MAX_THREADS);
        return 1;
    }

    m1 = malloc((size_t) tam * tam * sizeof(int));
    m2 = malloc((size_t) tam * tam * sizeof(int));
    prod = malloc((size_t) tam * tam * sizeof(int));
    if (m1 == NULL || m2 == NULL || prod == NULL) {
        fprintf(stderr, "Falha ao alocar as matrizes\n");
        return 1;
    }

    //inicializando matrizes (igual as versoes sequencial e pthreads)
    for (i = 0; i < tam; i++) {
        for (j = 0; j < tam; j++) {
            m1[i * tam + j] = i;
            m2[i * tam + j] = 2;
            prod[i * tam + j] = 0;
        }
    }

    //define quantas threads o OpenMP vai criar na regiao paralela
    omp_set_num_threads(num_threads);

    //medindo tempo (inclui criacao e encerramento das threads pelo OpenMP)
    gettimeofday(&start, NULL);

    //O OpenMP divide as iteracoes do loop de i (linhas de prod) entre as
    //threads. schedule(static) entrega blocos contiguos de linhas, a mesma
    //divisao feita a mao na versao pthreads. Como cada thread escreve so
    //nas suas linhas, nao e preciso mutex. As variaveis declaradas dentro
    //do loop (j, x, acumulador) sao privadas de cada thread.
    #pragma omp parallel for schedule(static)
    for (int li = 0; li < tam; li++) {
        for (int lj = 0; lj < tam; lj++) {
            int acumulador = 0;
            for (int x = 0; x < tam; x++) {
                acumulador += m1[li * tam + x] * m2[x * tam + lj];
            }
            prod[li * tam + lj] = acumulador;
        }
    }

    //Contabiliza tempo
    gettimeofday(&end, NULL);
    tempo_us = (end.tv_sec - start.tv_sec) * 1000000L
               + (end.tv_usec - start.tv_usec);

    printf("Versao OpenMP | matriz %dx%d | %d threads\n", tam, tam, num_threads);
    printf("Tempo transcorrido: %ld us (%.3f ms)\n", tempo_us, tempo_us / 1000.0);

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

    free(m1);
    free(m2);
    free(prod);
    return 0;
}
