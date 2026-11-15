#!/usr/bin/env bash
# Mede os tempos da versao sequencial e da versao OpenMP (parte 2).
#
# Uso (a partir da raiz do repositorio):
#   bash scripts/benchmark_openmp.sh
#
# Gera resultados/openmp.csv com uma linha por execucao:
#   versao,tamanho,threads,repeticao,tempo_us,soma
#
# Para resultados confiaveis, feche outros programas (navegador, jogos)
# enquanto o script roda.

set -euo pipefail

# Tamanhos aceitos pela versao sequencial atual: 10, 100 e 1000
# (pequena, media e grande).
TAMANHOS="10 100 1000"
# 1 thread serve de base para o speedup do proprio OpenMP.
THREADS="1 2 4 8 16"
REPETICOES=${REPETICOES:-5}

BUILD=build
SAIDA=resultados/openmp.csv

# Compila em modo Release (-O2), como pede o README
cmake -S . -B "$BUILD" -DCMAKE_BUILD_TYPE=Release > /dev/null
cmake --build "$BUILD" > /dev/null

mkdir -p resultados
echo "versao,tamanho,threads,repeticao,tempo_us,soma" > "$SAIDA"

# Extrai o tempo (us) e a soma de verificacao da saida de um programa
extrai() {
    local saida="$1"
    local tempo soma
    tempo=$(echo "$saida" | sed -n 's/^Tempo transcorrido: \([0-9]*\) us.*/\1/p')
    soma=$(echo "$saida" | sed -n 's/^Soma de verificacao: \([0-9-]*\).*/\1/p')
    echo "$tempo,$soma"
}

echo "Nucleos logicos nesta maquina: $(nproc)"
echo "Gravando em $SAIDA"

for tam in $TAMANHOS; do
    for rep in $(seq 1 "$REPETICOES"); do
        echo "sequencial | ${tam}x${tam} | repeticao $rep"
        out=$("./$BUILD/sequencial" "$tam")
        echo "sequencial,$tam,1,$rep,$(extrai "$out")" >> "$SAIDA"
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
