#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
#include <sys/time.h>

#define MAX_THREADS 4

//Dados (compartilhados entre as threads), alocados em tempo de execucao.
//Cada matriz e um vetor contiguo; o elemento [i][j] fica em [i * tam + j].
int *m1, *m2, *prod;
int tam;

//Faixa de linhas que cada thread calcula: [linha_inicio, linha_fim)
typedef struct {
    int id;
    int linha_inicio;
    int linha_fim;
} ArgsThread;

//Cada thread calcula um bloco de linhas de prod.
//Como as linhas nao se sobrepoem, nenhuma thread escreve na mesma
//posicao que outra, entao nao e preciso mutex.
void* multiplica_faixa(void* arg) {
    ArgsThread* a = (ArgsThread*) arg;

    for (int i = a->linha_inicio; i < a->linha_fim; i++) {
        for (int j = 0; j < tam; j++) {
            int acumulador = 0;
            for (int x = 0; x < tam; x++) {
                acumulador += m1[i * tam + x] * m2[x * tam + j];
            }
            prod[i * tam + j] = acumulador;
        }
    }
    return NULL;
}

int main(int argc, char* argv[]) {
    pthread_t threads[MAX_THREADS];
    ArgsThread args[MAX_THREADS];
    struct timeval start, end;
    long tempo_us;
    long long soma = 0;
    int num_threads = 2;
    int i, j;

    //linha de comando: ./paralelo [tamanho] [threads]
    //  tamanho: 10 | 100 | 1000   threads: 2 | 4
    tam = 1000;
    if (argc > 1) {
        tam = atoi(argv[1]);
    }
    if (argc > 2) {
        num_threads = atoi(argv[2]);
    }
    if ((tam != 10 && tam != 100 && tam != 1000)
        || (num_threads != 2 && num_threads != 4) || argc > 3) {
        fprintf(stderr, "Uso: %s [10|100|1000] [2|4]\n", argv[0]);
        return 1;
    }

    m1 = malloc((size_t) tam * tam * sizeof(int));
    m2 = malloc((size_t) tam * tam * sizeof(int));
    prod = malloc((size_t) tam * tam * sizeof(int));
    if (m1 == NULL || m2 == NULL || prod == NULL) {
        fprintf(stderr, "Falha ao alocar as matrizes\n");
        return 1;
    }

    //inicializando matrizes (igual a versao sequencial)
    for (i = 0; i < tam; i++) {
        for (j = 0; j < tam; j++) {
            m1[i * tam + j] = i;
            m2[i * tam + j] = 2;
            prod[i * tam + j] = 0;
        }
    }

    //dividindo as linhas entre as threads; as primeiras recebem
    //uma linha a mais quando a divisao nao e exata
    int base = tam / num_threads;
    int resto = tam % num_threads;
    int linha = 0;
    for (int t = 0; t < num_threads; t++) {
        args[t].id = t + 1;
        args[t].linha_inicio = linha;
        linha += base + (t < resto ? 1 : 0);
        args[t].linha_fim = linha;
    }

    //medindo tempo (inclui criacao e espera das threads)
    gettimeofday(&start, NULL);

    for (int t = 0; t < num_threads; t++) {
        if (pthread_create(&threads[t], NULL, multiplica_faixa, &args[t]) != 0) {
            fprintf(stderr, "Thread %d falhou ao ser criada\n", t + 1);
            return 1;
        }
    }
    for (int t = 0; t < num_threads; t++) {
        if (pthread_join(threads[t], NULL) != 0) {
            fprintf(stderr, "Thread %d falhou no join\n", t + 1);
            return 1;
        }
    }

    //Contabiliza tempo
    gettimeofday(&end, NULL);
    tempo_us = (end.tv_sec - start.tv_sec) * 1000000L
               + (end.tv_usec - start.tv_usec);

    printf("Versao paralela | matriz %dx%d | %d threads\n", tam, tam, num_threads);
    for (int t = 0; t < num_threads; t++) {
        printf("  Thread %d: linhas %d a %d\n",
               args[t].id, args[t].linha_inicio, args[t].linha_fim - 1);
    }
    printf("Tempo transcorrido: %ld us (%.3f ms)\n", tempo_us, tempo_us / 1000.0);

    //soma de verificacao: deve ser igual na versao sequencial
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
