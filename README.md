# MultiThreadMatrixMul

Multiplicação de matrizes quadradas em C, em duas versões, para comparar o tempo de execução:

| Programa     | Fonte          | Descrição                                                        |
|--------------|----------------|------------------------------------------------------------------|
| `sequencial` | `sequencial.c` | Multiplicação com um único fluxo de execução.                    |
| `paralelo`   | `main.c`       | Multiplicação dividida entre 2 ou 4 threads POSIX (`pthreads`). |

Na versão paralela, as linhas da matriz resultado são divididas em blocos contíguos, um por thread. Como nenhuma thread escreve nas linhas de outra, não é necessário mutex.

As matrizes são inicializadas com `m1[i][j] = i` e `m2[i][j] = 2`. Os dois programas imprimem uma **soma de verificação** (a soma de todos os elementos do produto), que deve ser igual nas duas versões para o mesmo tamanho de matriz.

## Requisitos

- Compilador C com suporte a C11 e `pthreads`:
  - **Linux / macOS:** `gcc` ou `clang`.
  - **Windows:** MinGW-w64 (por exemplo, via [MSYS2](https://www.msys2.org/), ambiente UCRT64). O MSVC não serve, porque não oferece `pthread.h` nem `sys/time.h`.
- [CMake](https://cmake.org/) 3.10 ou mais recente (opcional; também dá para compilar direto com `gcc`).

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

Os executáveis `sequencial` e `paralelo` ficam na pasta `build/`.

### Opção 2: gcc direto

```bash
gcc -O2 -std=c11 -o sequencial sequencial.c
gcc -O2 -std=c11 -pthread -o paralelo main.c
```

### Opção 3: CLion

Abra a pasta do projeto no CLion. Ele detecta o `CMakeLists.txt` e cria as configurações de execução `sequencial` e `paralelo`. Para passar argumentos, use *Run → Edit Configurations… → Program arguments*.

## Como executar

```text
sequencial [tamanho]
paralelo   [tamanho] [threads]
```

| Argumento | Valores aceitos     | Padrão |
|-----------|---------------------|--------|
| `tamanho` | `10`, `100`, `1000` | `1000` |
| `threads` | `2`, `4`            | `2`    |

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

O tempo é medido com `gettimeofday` e exibido em microssegundos e milissegundos. Ele cobre apenas a multiplicação (na versão paralela, inclui também a criação e o `join` das threads). Alocação, inicialização e impressão ficam de fora.

Para comparar as versões, compile em modo **Release** (`-O2`): no modo Debug, sem otimização, os tempos não representam bem o desempenho real. Como o tempo varia entre execuções, rode cada caso algumas vezes e use a média.

## Estrutura

```text
.
├── CMakeLists.txt   # build dos dois executáveis
├── main.c           # versão paralela (pthreads)
├── sequencial.c     # versão sequencial
└── README.md
```
