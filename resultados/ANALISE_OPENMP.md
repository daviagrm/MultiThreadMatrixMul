# Parte 2: análise dos resultados da versão OpenMP

## Ambiente de teste

- Windows com Ubuntu no WSL2, processador com **8 núcleos lógicos** (`nproc` = 8)
- Compilação em modo Release (`-O2`) com `gcc -fopenmp`, via CMake
- Matrizes de 10×10, 100×100 e 1000×1000, inicializadas como nas outras versões
- 1, 2, 4, 8 e 16 threads; **5 repetições** por caso, tempos abaixo são a média
- Dados brutos: [`openmp.csv`](openmp.csv). Resumo: [`openmp_resumo.csv`](openmp_resumo.csv)

A soma de verificação foi igual à da versão sequencial em todas as 90 execuções, ou seja, o OpenMP calculou o produto corretamente em todos os casos.

## Como o speedup foi calculado

- **speedup_1t** = tempo do OpenMP com 1 thread ÷ tempo do OpenMP com N threads
- **eficiência** = speedup_1t ÷ N

Usamos o OpenMP com 1 thread como base, e não a versão sequencial, porque a versão sequencial atual acumula o resultado direto na matriz (`prod[i*tam+j] +=`), enquanto o OpenMP usa uma variável local (`acumulador`). Por isso o OpenMP com **1 thread** já é cerca de 3,4× mais rápido que a sequencial, e o speedup em relação a ela sai inflado (chega a 9,8× com 8 threads, acima do máximo teórico de 8×).

## Matriz 1000×1000 (resultado principal)

| Threads | Tempo médio | Speedup | Eficiência |
|---|---|---|---|
| 1 | 880 ms | 1,00× | 100% |
| 2 (menos que os núcleos) | 541 ms | 1,63× | 81% |
| 4 (menos que os núcleos) | 390 ms | 2,26× | 56% |
| 8 (igual aos núcleos) | 308 ms | **2,86×** | 36% |
| 16 (mais que os núcleos) | 311 ms | 2,83× | 18% |

- O speedup cresce até 8 threads e **estabiliza**: com 16 threads não há ganho, pois não existem mais núcleos; as threads extras só se revezam nos mesmos núcleos.
- O ganho fica abaixo do ideal (2,86× em vez de 8×). Causas prováveis:
  - parte dos 8 núcleos lógicos pode ser hyperthreading (núcleos físicos compartilhados);
  - a segunda matriz é lida coluna por coluna (`m2[x*tam+j]`), o que causa muitas falhas de cache e torna o acesso à memória o gargalo.

## Matrizes pequenas (10×10 e 100×100)

| Threads | 10×10 | 100×100 |
|---|---|---|
| 1 | 0,004 ms | 0,515 ms |
| 2 | 0,106 ms | 0,508 ms |
| 4 | 0,191 ms | 0,479 ms |
| 8 | **6,508 ms** | **10,568 ms** |
| 16 | 1,089 ms | 1,167 ms |

- Em 10×10, paralelizar **sempre piora**: criar e sincronizar as threads custa mais que a multiplicação inteira.
- Em 100×100, o ganho é praticamente nulo (no máximo 1,08× com 4 threads).

## Anomalia: 8 threads em matrizes pequenas

Com exatamente 8 threads (igual ao número de núcleos), os tempos de 10×10 e 100×100 ficam muito acima dos vizinhos. O atraso apareceu nas **5 repetições**, então não é ruído de uma execução isolada.

Hipótese: com 8 threads, o OpenMP ocupa todos os núcleos. Quando o Windows ou o WSL precisa de um núcleo, uma das threads é interrompida, e o OpenMP só termina a região paralela quando a última thread termina. Por padrão, as threads que já terminaram ficam esperando ativamente (ocupando o núcleo), o que piora a disputa. Com 16 threads, o OpenMP detecta que há mais threads que núcleos e reduz a espera ativa, por isso o tempo volta a cair.

Teste que confirma a hipótese (matriz 100×100):

| Configuração | Tempo |
|---|---|
| 7 threads (sobra 1 núcleo para o sistema) | 0,86 ms |
| 8 threads, configuração padrão | **5,06 ms** |
| 8 threads com `OMP_WAIT_POLICY=passive` | 1,02 ms |

Na matriz 1000×1000 esse atraso de alguns milissegundos é desprezível perto dos ~300 ms da multiplicação, e por isso não aparece.

## Conclusões

1. Para matrizes grandes, o OpenMP reduz o tempo de 880 ms para 308 ms (2,86×) com 8 threads, com o ganho limitado pelo número de núcleos.
2. Usar mais threads que núcleos não traz ganho.
3. Para matrizes pequenas, o custo de criar e coordenar as threads é maior que o próprio cálculo, e a versão paralela é mais lenta.
4. Ocupar todos os núcleos nem sempre é melhor: com 8 threads em 8 núcleos, interrupções do sistema operacional atrasam a região paralela inteira.
5. Em relação à parte 1 (pthreads), o OpenMP chega ao mesmo tipo de divisão de trabalho (blocos contíguos de linhas) com uma única diretiva, sem precisar criar, dividir e esperar as threads manualmente.

## Observação sobre a variação dos tempos

Alguns casos variaram bastante entre repetições (por exemplo, a sequencial 1000×1000 ficou entre 2,1 s e 3,5 s). Isso é típico de notebooks, em que o processador muda de frequência por energia ou temperatura. Para medições mais estáveis, convém rodar com o carregador ligado e o Windows no modo de energia "Melhor desempenho".
