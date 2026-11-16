# MultiThreadMatrixMul

Multiplicação de matrizes quadradas em C, em cinco versões (três na CPU e duas na GPU), para comparar o tempo de execução:

| Programa     | Fonte          | Descrição                                                        |
|--------------|----------------|------------------------------------------------------------------|
| `sequencial` | `sequencial.c` | Multiplicação com um único fluxo de execução.                    |
| `paralelo`   | `main.c`       | Multiplicação dividida entre 2 ou 4 threads POSIX (`pthreads`). |
| `openmp`     | `openmp.c`     | Multiplicação paralelizada com OpenMP (1 a 64 threads).          |
| `cuda`       | `cuda.cu`      | Multiplicação na GPU com CUDA (só GPUs NVIDIA).                  |
| `opencl`     | `opencl.c`     | Multiplicação na GPU com OpenCL (GPUs AMD, NVIDIA e Intel).      |

Na versão paralela, as linhas da matriz resultado são divididas em blocos contíguos, um por thread. Como nenhuma thread escreve nas linhas de outra, não é necessário mutex.

Na versão OpenMP, a mesma divisão é feita pela diretiva `#pragma omp parallel for schedule(static)` sobre o loop das linhas: o OpenMP cria as threads, entrega a cada uma um bloco contíguo de linhas e espera todas terminarem. O número de threads é definido com `omp_set_num_threads`.

Nas versões de GPU, cada thread da GPU calcula um elemento do produto. As threads são agrupadas em blocos 2D (8×8, 16×16 ou 32×32) e os blocos numa grade que cobre a matriz inteira. O programa copia `m1` e `m2` para a GPU, executa o *kernel* e copia o resultado de volta. As duas versões usam o mesmo kernel. A CUDA só roda em GPUs NVIDIA. A OpenCL roda em GPUs de qualquer fabricante (inclusive GPUs integradas ao processador), para que quem tem placa AMD ou Intel também possa medir a GPU.

As matrizes são inicializadas com `m1[i][j] = i` e `m2[i][j] = 2`. Todos os programas imprimem uma **soma de verificação** (a soma de todos os elementos do produto), que deve ser igual em todas as versões para o mesmo tamanho de matriz.

## Requisitos

- Compilador C com suporte a C11, `pthreads` e OpenMP:
  - **Linux:** `gcc` (o OpenMP já vem com o `build-essential`).
  - **macOS:** `clang` com a biblioteca `libomp` (`brew install libomp`).
  - **Windows:** MinGW-w64 (por exemplo, via [MSYS2](https://www.msys2.org/), ambiente UCRT64). O MSVC não serve, porque não oferece `pthread.h` nem `sys/time.h`.
- Para a versão CUDA (opcional): GPU NVIDIA e o [CUDA Toolkit](https://developer.nvidia.com/cuda-downloads) (`nvcc`). No WSL2 basta o driver NVIDIA do Windows e o toolkit instalado no Ubuntu; o `nvcc` fica em `/usr/local/cuda/bin`, que normalmente não está no `PATH`.
- Para a versão OpenCL (opcional): qualquer GPU com driver OpenCL, mais os cabeçalhos e a biblioteca do OpenCL para compilar:
  - **Linux:** `sudo apt install ocl-icd-opencl-dev`, além do driver OpenCL da GPU: AMD com [ROCm](https://rocm.docs.amd.com/) ou Mesa (`mesa-opencl-icd`), Intel com `intel-opencl-icd`, NVIDIA com o próprio driver. Para conferir se a GPU aparece, use `clinfo`.
  - **Windows:** o driver de vídeo (AMD, NVIDIA ou Intel) já traz o OpenCL. Para compilar, use os cabeçalhos e o `OpenCL.lib` do [OpenCL SDK da Khronos](https://github.com/KhronosGroup/OpenCL-SDK/releases) ou do CUDA Toolkit, com o MSVC ou o MinGW (veja abaixo).
  - **WSL2:** o WSL2 não tem driver OpenCL para as GPUs por padrão; compile e rode a versão OpenCL direto no Windows.
  - **macOS:** já vem no sistema (`-framework OpenCL`), mas a Apple deixou de atualizá-lo.
- [CMake](https://cmake.org/) 3.10 ou mais recente (opcional; também dá para compilar direto com `gcc`). Sem compilador CUDA ou sem OpenCL, o CMake pula essas versões e compila o resto.

## Como compilar

### Opção 1: CMake

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

No Windows com MinGW, indique o gerador:

```bash
cmake -S . -B build -G "MinGW Makefiles" -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

Os executáveis `sequencial`, `paralelo`, `openmp`, `cuda` (se houver CUDA) e `opencl` (se houver OpenCL) ficam na pasta `build/`.

O CMake só encontra o `nvcc` se ele estiver no `PATH`. No Linux/WSL, rode antes `export PATH=/usr/local/cuda/bin:$PATH` ou passe `-DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc`. Se a mensagem "OpenCL nao encontrado" aparecer mesmo com o OpenCL instalado, indique o caminho com `-DOpenCL_INCLUDE_DIR=<pasta include> -DOpenCL_LIBRARY=<arquivo libOpenCL.so>`.

### Opção 2: gcc direto

```bash
gcc -O2 -std=c11 -o sequencial sequencial.c
gcc -O2 -std=c11 -pthread -o paralelo main.c
gcc -O2 -std=c11 -fopenmp -o openmp openmp.c
nvcc -O2 -arch=native -o cuda cuda.cu   # versão CUDA
gcc -O2 -std=c11 -o opencl opencl.c -lOpenCL   # versão OpenCL (Linux/MinGW)
```

A versão OpenCL no Windows com o MSVC, no *x64 Native Tools Command Prompt for VS*. `%OPENCL%` é a pasta do OpenCL SDK; com o CUDA Toolkit, use `%CUDA_PATH%`:

```bat
cl /O2 /std:c11 /I "%OPENCL%\include" opencl.c /Fe:build\opencl.exe /link /LIBPATH:"%OPENCL%\lib\x64" OpenCL.lib
```

### Opção 3: CLion

Abra a pasta do projeto no CLion. Ele detecta o `CMakeLists.txt` e cria as configurações de execução `sequencial`, `paralelo` e `openmp`. Para passar argumentos, use *Run → Edit Configurations… → Program arguments*.

## Como executar

```text
sequencial [tamanho]
paralelo   [tamanho] [threads]
openmp     [tamanho] [threads]
cuda       [tamanho] [lado do bloco]
opencl     [tamanho] [lado do bloco] [gpu]
opencl     --listar
```

| Argumento | Valores aceitos     | Padrão |
|-----------|---------------------|--------|
| `tamanho` | `10`, `100`, `1000` | `1000` |
| `threads` | `2`, `4`            | `2`    |

No `openmp`, o tamanho pode ser qualquer inteiro ≥ 1 e o número de threads vai de 1 a 64 (padrão: 1000 e 2).

No `cuda` e no `opencl`, o tamanho pode ser qualquer inteiro ≥ 1 e o lado do bloco é `8`, `16` ou `32` (64, 256 ou 1024 threads por bloco; padrão: 1000 e 16). Algumas GPUs (várias da AMD e a NVIDIA via OpenCL) não aceitam 32×32, e o programa avisa quando isso acontece. No `opencl`, `--listar` mostra as GPUs encontradas, e o terceiro argumento escolhe qual usar (padrão: `0`, a primeira).

Exemplos (a partir da pasta `build/`; no Windows, use `.\sequencial.exe` etc.):

```bash
./sequencial 1000
./paralelo 1000 4
./paralelo 10 2      # matrizes 10x10 também imprimem o resultado completo
```

Saída de exemplo:

```text
Versao paralela | matriz 1000x1000 | 4 threads
  Thread 1: linhas 0 a 249
  Thread 2: linhas 250 a 499
  Thread 3: linhas 500 a 749
  Thread 4: linhas 750 a 999
Tempo transcorrido: 215264 us (215.264 ms)
Soma de verificacao: 999000000000
```

Valores fora da lista aceita fazem o programa mostrar a mensagem de uso e sair com código 1.

## Medição de tempo

O tempo é medido com `gettimeofday` e exibido em microssegundos e milissegundos. Ele cobre apenas a multiplicação (nas versões paralelas, inclui também a criação e o encerramento das threads). Alocação, inicialização e impressão ficam de fora.

Nas versões de GPU, o tempo é medido pelos contadores da própria GPU (`cudaEvent` no CUDA, *profiling events* no OpenCL) e aparece de duas formas: **Tempo transcorrido** inclui as cópias CPU→GPU e GPU→CPU (para comparar com as versões de CPU, que já têm os dados na memória), e **Tempo do kernel** é só a multiplicação na GPU. Antes da medição, o kernel roda uma vez para aquecimento, porque a primeira chamada carrega o código na GPU.

Para comparar as versões, compile em modo **Release** (`-O2`): no modo Debug, sem otimização, os tempos não representam bem o desempenho real. Como o tempo varia entre execuções, rode cada caso algumas vezes e use a média.

## Testes de desempenho

```bash
sudo apt install -y python3-matplotlib   # uma vez
bash scripts/benchmark_openmp.sh          # mede e grava resultados/openmp.csv
python3 scripts/graficos_openmp.py        # gera tabela e gráficos
```

O script mede as três versões: a sequencial, a pthreads (2 e 4 threads) e a OpenMP (1, 2, 4, 8 e 16 threads, além do número de núcleos da máquina e do dobro dele). Variáveis opcionais: `REPETICOES` (padrão: 5) e `THREADS` (lista de threads do OpenMP), por exemplo `REPETICOES=10 bash scripts/benchmark_openmp.sh`. Sem CMake instalado, ele compila direto com `gcc`. O número de núcleos fica gravado em `resultados/nucleos.txt`, para que os gráficos possam ser gerados em outra máquina.

Para a GPU, rode o benchmark acima primeiro, porque o gráfico comparativo usa os resultados da CPU. Depois, rode um ou os dois scripts abaixo, conforme a GPU:

```bash
bash scripts/benchmark_cuda.sh            # GPU NVIDIA: grava resultados/cuda.csv
bash scripts/benchmark_opencl.sh          # qualquer GPU: grava resultados/opencl.csv
python3 scripts/graficos_gpu.py           # gera tabela e gráficos comparativos
```

- O `benchmark_opencl.sh` mede **todas** as GPUs encontradas (por exemplo, a integrada e a dedicada).
- No Linux, o script compila o `opencl.c` com `gcc`. No Windows, compile antes o `build\opencl.exe` (veja *Como compilar*) e rode o script no Git Bash ou no MSYS2.
- Os scripts medem blocos de 8×8, 16×16 e 32×32. Variáveis opcionais: `REPETICOES` e `LADOS`.
- O `graficos_gpu.py` usa os resultados de GPU que existirem (CUDA, OpenCL ou os dois).

Análises: [`resultados/ANALISE_OPENMP.md`](resultados/ANALISE_OPENMP.md) (CPU) e [`resultados/ANALISE_GPU.md`](resultados/ANALISE_GPU.md) (GPUs e comparação geral).

## Estrutura

```text
.
├── CMakeLists.txt   # build dos executáveis
├── cuda.cu          # versão na GPU (CUDA)
├── main.c           # versão paralela (pthreads)
├── opencl.c         # versão na GPU (OpenCL: AMD, NVIDIA e Intel)
├── openmp.c         # versão paralela (OpenMP)
├── sequencial.c     # versão sequencial
├── scripts/         # testes de desempenho
├── resultados/      # tempos, gráficos e análise
└── README.md
```
