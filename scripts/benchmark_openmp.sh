#!/usr/bin/env bash
# Mede os tempos das versoes sequencial, pthreads (parte 1) e OpenMP (parte 2).
#
# Uso (a partir da raiz do repositorio):
#   bash scripts/benchmark_openmp.sh
#
# Gera resultados/openmp.csv com uma linha por execucao:
#   versao,tamanho,threads,repeticao,tempo_us,soma
# e resultados/nucleos.txt com o numero de nucleos logicos da maquina
# (usado pelos graficos).
#
# Para resultados confiaveis, feche outros programas (navegador, jogos)
# enquanto o script roda.

set -euo pipefail

# Tamanhos aceitos pelas versoes sequencial e pthreads: 10, 100 e 1000
# (pequena, media e grande).
TAMANHOS="10 100 1000"
# 1 thread serve de base para o speedup do proprio OpenMP. Inclui o numero
# de nucleos e o dobro dele, para ter casos com menos, igual e mais threads
# que nucleos em qualquer maquina.
NUCLEOS=$(nproc)
THREADS=${THREADS:-$(printf '%s\n' 1 2 4 8 16 "$NUCLEOS" $((2 * NUCLEOS)) | sort -nu | tr '\n' ' ')}
# A versao pthreads aceita apenas 2 ou 4 threads.
THREADS_PTHREADS="2 4"
REPETICOES=${REPETICOES:-5}

BUILD=build
SAIDA=resultados/openmp.csv

# Compila em modo Release (-O2), como pede o README.
# Sem CMake, compila direto com gcc usando as mesmas opcoes.
if command -v cmake > /dev/null; then
    cmake -S . -B "$BUILD" -DCMAKE_BUILD_TYPE=Release > /dev/null
    cmake --build "$BUILD" > /dev/null
else
    mkdir -p "$BUILD"
    gcc -O2 -std=c11 -o "$BUILD/sequencial" sequencial.c
    gcc -O2 -std=c11 -pthread -o "$BUILD/paralelo" main.c
    gcc -O2 -std=c11 -fopenmp -o "$BUILD/openmp" openmp.c
fi

mkdir -p resultados
echo "versao,tamanho,threads,repeticao,tempo_us,soma" > "$SAIDA"
echo "$NUCLEOS" > resultados/nucleos.txt

# Extrai o tempo (us) e a soma de verificacao da saida de um programa
extrai() {
    local saida="$1"
    local tempo soma
    tempo=$(echo "$saida" | sed -n 's/^Tempo transcorrido: \([0-9]*\) us.*/\1/p')
    soma=$(echo "$saida" | sed -n 's/^Soma de verificacao: \([0-9-]*\).*/\1/p')
    echo "$tempo,$soma"
}

echo "Nucleos logicos nesta maquina: $NUCLEOS | threads OpenMP: $THREADS"
echo "Gravando em $SAIDA"

for tam in $TAMANHOS; do
    for rep in $(seq 1 "$REPETICOES"); do
        echo "sequencial | ${tam}x${tam} | repeticao $rep"
        out=$("./$BUILD/sequencial" "$tam")
        echo "sequencial,$tam,1,$rep,$(extrai "$out")" >> "$SAIDA"
    done

    for t in $THREADS_PTHREADS; do
        for rep in $(seq 1 "$REPETICOES"); do
            echo "pthreads   | ${tam}x${tam} | $t threads | repeticao $rep"
            out=$("./$BUILD/paralelo" "$tam" "$t")
            echo "pthreads,$tam,$t,$rep,$(extrai "$out")" >> "$SAIDA"
        done
    done

    for t in $THREADS; do
        for rep in $(seq 1 "$REPETICOES"); do
            echo "openmp     | ${tam}x${tam} | $t threads | repeticao $rep"
            out=$("./$BUILD/openmp" "$tam" "$t")
            echo "openmp,$tam,$t,$rep,$(extrai "$out")" >> "$SAIDA"
        done
    done
done

echo
echo "Pronto: $(($(wc -l < "$SAIDA") - 1)) execucoes gravadas em $SAIDA"
echo "Para gerar a tabela e os graficos: python3 scripts/graficos_openmp.py"
