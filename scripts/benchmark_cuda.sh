#!/usr/bin/env bash
# Mede os tempos da versao CUDA (GPU).
#
# Uso (a partir da raiz do repositorio):
#   bash scripts/benchmark_cuda.sh
#
# Gera resultados/cuda.csv com uma linha por execucao:
#   gpu,tamanho,lado,repeticao,tempo_total_us,tempo_kernel_us,soma
# onde "lado" e o lado do bloco de threads (8 = 8x8 = 64 threads por bloco),
# tempo_total inclui as copias CPU->GPU e GPU->CPU e tempo_kernel e so a
# multiplicacao na GPU.
#
# As versoes de CPU sao medidas por scripts/benchmark_openmp.sh e a versao
# OpenCL (qualquer GPU) por scripts/benchmark_opencl.sh; o grafico
# comparativo (scripts/graficos_gpu.py) usa todos os resultados.

set -euo pipefail

TAMANHOS="10 100 1000"
LADOS=${LADOS:-"8 16 32"}
REPETICOES=${REPETICOES:-5}

BUILD=build
SAIDA=resultados/cuda.csv

# O nvcc costuma ficar fora do PATH no Linux/WSL
if ! command -v nvcc > /dev/null && [ -x /usr/local/cuda/bin/nvcc ]; then
    export PATH=/usr/local/cuda/bin:$PATH
fi
if ! command -v nvcc > /dev/null; then
    echo "nvcc nao encontrado: instale o CUDA Toolkit" >&2
    exit 1
fi

# -arch=native gera codigo para a GPU desta maquina
mkdir -p "$BUILD"
nvcc -O2 -arch=native -o "$BUILD/cuda" cuda.cu

mkdir -p resultados
echo "gpu,tamanho,lado,repeticao,tempo_total_us,tempo_kernel_us,soma" > "$SAIDA"

echo "GPU: $(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null || echo '?')"
echo "Gravando em $SAIDA"

for tam in $TAMANHOS; do
    for lado in $LADOS; do
        for rep in $(seq 1 "$REPETICOES"); do
            echo "cuda | ${tam}x${tam} | blocos ${lado}x${lado} | repeticao $rep"
            out=$("./$BUILD/cuda" "$tam" "$lado")
            total=$(echo "$out" | sed -n 's/^Tempo transcorrido: \([0-9]*\) us.*/\1/p')
            kernel=$(echo "$out" | sed -n 's/^Tempo do kernel: \([0-9]*\) us.*/\1/p')
            soma=$(echo "$out" | sed -n 's/^Soma de verificacao: \([0-9-]*\).*/\1/p')
            gpu=$(echo "$out" | sed -n 's/^GPU: //p' | sed 's/,//g')
            echo "$gpu,$tam,$lado,$rep,$total,$kernel,$soma" >> "$SAIDA"
        done
    done
done

echo
echo "Pronto: $(($(wc -l < "$SAIDA") - 1)) execucoes gravadas em $SAIDA"
echo "Para gerar a tabela e os graficos: python3 scripts/graficos_gpu.py"
