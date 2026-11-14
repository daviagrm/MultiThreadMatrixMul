#include <sys/time.h>
#include <stdio.h>
#include <stdlib.h>

//Dados: alocados em tempo de execucao, pois o tamanho vem da linha de comando.
//Cada matriz e um vetor contiguo; o elemento [i][j] fica em [i * tam + j].
int *m1, *m2, *prod;
int tam;

int main(int argc, char* argv[]) {
    struct timeval start, end;
    long tempo_us;
    long long soma = 0;
    int i, j;

    //tamanho pela linha de comando: ./sequencial 10 | 100 | 1000
    tam = 1000;
    if (argc > 1) {
        tam = atoi(argv[1]);
        if ((tam != 10 && tam != 100 && tam != 1000) || argc > 2) {
            fprintf(stderr, "Uso: %s [10|100|1000]\n", argv[0]);
            return 1;
        }
    }

    m1 = malloc((size_t) tam * tam * sizeof(int));
    m2 = malloc((size_t) tam * tam * sizeof(int));
    prod = malloc((size_t) tam * tam * sizeof(int));
    if (m1 == NULL || m2 == NULL || prod == NULL) {
        fprintf(stderr, "Falha ao alocar as matrizes\n");
        return 1;
    }

    //inicializando matrizes
    for (i = 0; i < tam; i++) {
        for (j = 0; j < tam; j++) {
            m1[i * tam + j] = i;
            m2[i * tam + j] = 2;
            prod[i * tam + j] = 0;
        }
    }
    //medindo tempo
    gettimeofday(&start, NULL);

    for (i = 0; i < tam; i++) {
        for (j = 0; j < tam; j++) {
            for (int x = 0; x < tam; x++) {
                prod[i * tam + j] += m1[i * tam + x] * m2[x * tam + j];
            }
        }
    }

    //Contabiliza tempo (em microssegundos, para nao zerar em matrizes pequenas)
    gettimeofday(&end, NULL);
    tempo_us = (end.tv_sec - start.tv_sec) * 1000000L
               + (end.tv_usec - start.tv_usec);

    printf("Versao sequencial | matriz %dx%d\n", tam, tam);
    printf("Tempo transcorrido: %ld us (%.3f ms)\n", tempo_us, tempo_us / 1000.0);

    //soma de verificacao: deve ser igual na versao paralela
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
