#!/usr/bin/env bash
# Mede os tempos da versao OpenCL em TODAS as GPUs encontradas
# (AMD, NVIDIA ou Intel).
#
# Uso (a partir da raiz do repositorio):
#   bash scripts/benchmark_opencl.sh
#
# Linux: compila com gcc. Precisa do pacote de desenvolvimento do OpenCL
#   (Ubuntu: sudo apt install ocl-icd-opencl-dev) e do driver OpenCL da GPU
#   (AMD: ROCm ou Mesa; Intel: intel-opencl-icd; NVIDIA: o proprio driver).
# Windows: compile antes o build/opencl.exe (veja o README) e rode este
#   script no Git Bash ou no MSYS2; o driver de video ja traz o OpenCL.
#
# Gera resultados/opencl.csv com uma linha por execucao:
#   gpu,tamanho,lado,repeticao,tempo_total_us,tempo_kernel_us,soma

set -euo pipefail

TAMANHOS="10 100 1000"
LADOS=${LADOS:-"8 16 32"}
REPETICOES=${REPETICOES:-5}

BUILD=build
SAIDA=resultados/opencl.csv
mkdir -p "$BUILD" resultados

# Compila se houver gcc com a biblioteca OpenCL; senao, usa o executavel
# que ja estiver em build/ (no Windows, compilado com o MSVC ou o MinGW).
if [ "$(uname)" = "Darwin" ]; then
    gcc -O2 -std=c11 -o "$BUILD/opencl" opencl.c -framework OpenCL
elif command -v gcc > /dev/null && gcc -O2 -std=c11 -o "$BUILD/opencl" opencl.c -lOpenCL 2> /dev/null; then
    :
fi
if [ -x "$BUILD/opencl" ]; then
    BIN="$BUILD/opencl"
elif [ -x "$BUILD/opencl.exe" ]; then
    BIN="$BUILD/opencl.exe"
else
    echo "Nao foi possivel compilar o opencl.c. Instale o OpenCL (veja o README)." >&2
    exit 1
fi

if ! "$BIN" --listar > /dev/null 2>&1; then
    "$BIN" 10 >&2 || true   # mostra a mensagem de erro do programa
    exit 1
fi

echo "gpu,tamanho,lado,repeticao,tempo_total_us,tempo_kernel_us,soma" > "$SAIDA"
echo "GPUs encontradas:"
"$BIN" --listar | tr -d '\r'
echo "Gravando em $SAIDA"

n_gpus=$("$BIN" --listar | wc -l)
for g in $(seq 0 $((n_gpus - 1))); do
    # nome da GPU sem o indice e sem o nome da plataforma
    gpu=$("$BIN" --listar | tr -d '\r' | sed -n "$((g + 1))p" \
          | sed 's/^[0-9]*: //; s/ (.*)$//; s/,//g')
    for tam in $TAMANHOS; do
        for lado in $LADOS; do
            for rep in $(seq 1 "$REPETICOES"); do
                if ! out=$("$BIN" "$tam" "$lado" "$g" 2>&1); then
                    # por exemplo, GPU que nao aceita blocos de 32x32
                    echo "$gpu | blocos ${lado}x${lado}: $(echo "$out" | tr -d '\r' | tail -1)"
                    break
                fi
                out=$(echo "$out" | tr -d '\r')
                echo "opencl | $gpu | ${tam}x${tam} | blocos ${lado}x${lado} | repeticao $rep"
                total=$(echo "$out" | sed -n 's/^Tempo transcorrido: \([0-9]*\) us.*/\1/p')
                kernel=$(echo "$out" | sed -n 's/^Tempo do kernel: \([0-9]*\) us.*/\1/p')
                soma=$(echo "$out" | sed -n 's/^Soma de verificacao: \([0-9-]*\).*/\1/p')
                echo "$gpu,$tam,$lado,$rep,$total,$kernel,$soma" >> "$SAIDA"
            done
        done
    done
done

echo
echo "Pronto: $(($(wc -l < "$SAIDA") - 1)) execucoes gravadas em $SAIDA"
echo "Para gerar a tabela e os graficos: python3 scripts/graficos_gpu.py"
