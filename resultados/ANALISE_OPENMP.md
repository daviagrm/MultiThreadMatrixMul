# Parte 2: análise dos resultados da versão OpenMP

## Ambiente de teste

- Windows 11 com Ubuntu no WSL2
- Processador Intel Core Ultra 7 155H, com **22 núcleos lógicos** (`nproc` = 22). É um processador híbrido: 6 núcleos de desempenho com hyperthreading (12 threads), 8 núcleos de eficiência e 2 núcleos de baixo consumo, ou seja, 16 núcleos físicos de velocidades diferentes.
- Compilação em modo Release (`-O2`) com `gcc`: `-pthread` na versão pthreads e `-fopenmp` na versão OpenMP
- Matrizes de 10×10, 100×100 e 1000×1000, inicializadas igual nas três versões
- OpenMP com 1, 2, 4, 8, 16, 22 e 44 threads; pthreads com 2 e 4 threads (os valores que a parte 1 aceita)
- **10 repetições** por caso; os tempos abaixo são a média
- Dados brutos: [`openmp.csv`](openmp.csv). Resumo com desvio padrão: [`openmp_resumo.csv`](openmp_resumo.csv)

A soma de verificação foi igual nas três versões em todas as 300 execuções, ou seja, todas calcularam o produto corretamente.

## Como o speedup foi calculado

- **speedup** = tempo da versão sequencial ÷ tempo da versão paralela
- **eficiência** = speedup ÷ número de threads

As três versões usam o mesmo laço: o produto de cada posição é somado numa variável local (`acumulador`) e gravado na matriz uma vez só. Por isso, a diferença de tempo entre elas vem apenas do paralelismo. Prova disso é que o OpenMP com 1 thread leva o mesmo tempo que a sequencial na matriz 1000×1000 (421,7 ms contra 422,0 ms).

## Matriz 1000×1000 (resultado principal)

| Threads | Sequencial | pthreads | OpenMP | Speedup (OpenMP) | Eficiência (OpenMP) |
| --- | --- | --- | --- | --- | --- |
| 1 | 422 ms | – | 422 ms | 1,00× | 100% |
| 2 | – | 240 ms | 241 ms | 1,75× | 88% |
| 4 | – | 148 ms | 142 ms | 2,96× | 74% |
| 8 | – | – | 104 ms | 4,06× | 51% |
| 16 | – | – | 94 ms | **4,47×** | 28% |
| 22 (igual aos núcleos lógicos) | – | – | 103 ms | 4,10× | 19% |
| 44 (o dobro dos núcleos) | – | – | 96 ms | 4,39× | 10% |

- **pthreads e OpenMP empatam.** Com 2 e 4 threads, os tempos ficam a menos de 5% um do outro, diferença dentro do desvio padrão (de 9 a 22 ms). Faz sentido, porque as duas versões dividem as linhas do mesmo jeito, em blocos contíguos.
- O speedup cresce bem até 4 threads e passa a crescer devagar a partir de 8. Depois de 16 threads ele **estabiliza em torno de 4,1× a 4,5×**: com 22 ou 44 threads não há ganho.
- O ganho fica bem abaixo do ideal (4,5× em vez de 16× ou 22×). Causas prováveis:
  - **acesso à memória:** a segunda matriz é lida coluna por coluna (`m2[x*tam+j]`), o que causa muitas falhas de cache. Com várias threads fazendo isso ao mesmo tempo, o barramento de memória vira o gargalo, e mais threads não ajudam;
  - **núcleos diferentes:** dos 22 núcleos lógicos, só 6 são de desempenho. Os de eficiência são mais lentos, e como `schedule(static)` dá a cada thread a mesma quantidade de linhas, a região paralela espera pela thread mais lenta;
  - **hyperthreading:** as duas threads de um núcleo de desempenho dividem o mesmo núcleo físico.

## Matrizes pequenas (10×10 e 100×100)

| Threads | 10×10 | 100×100 |
| --- | --- | --- |
| Sequencial | < 0,001 ms | 0,371 ms |
| pthreads, 2 | 0,146 ms | 0,304 ms |
| pthreads, 4 | 0,205 ms | 0,294 ms |
| OpenMP, 1 | 0,004 ms | 0,318 ms |
| OpenMP, 2 | 0,083 ms | 0,250 ms |
| OpenMP, 4 | 0,152 ms | **0,230 ms** |
| OpenMP, 8 | 0,256 ms | 0,498 ms |
| OpenMP, 16 | **10,800 ms** | **10,807 ms** |
| OpenMP, 22 | **11,446 ms** | **16,936 ms** |
| OpenMP, 44 | 2,031 ms | 1,990 ms |

- Em 10×10, paralelizar **sempre piora**: a multiplicação inteira leva menos de 1 µs, e só criar as threads já custa de 80 µs a 200 µs.
- Em 100×100, há um ganho pequeno com poucas threads (até 1,6× com 4 threads no OpenMP). Com 8 ou mais, o custo de coordenar as threads passa a ser maior que o ganho.
- Nas duas, o OpenMP com 2 e 4 threads é um pouco mais rápido que o pthreads. Uma possível explicação é que o runtime do OpenMP (libgomp) reaproveita a thread principal como uma das trabalhadoras, enquanto a versão pthreads cria todas as threads e deixa a principal só esperando.

## Anomalia: 16 e 22 threads em matrizes pequenas

Com 16 e 22 threads, os tempos de 10×10 e 100×100 ficam muito acima dos vizinhos e variam bastante entre repetições (desvio de 2 a 7 ms). Com 44 threads, voltam a cair.

Hipótese: por padrão, quando uma thread do OpenMP termina sua parte, ela fica **esperando ativamente** (girando num laço e ocupando o núcleo) em vez de dormir. Quando há quase tantas threads quanto núcleos, essas threads paradas disputam os núcleos com as que ainda estão trabalhando e com o próprio Windows/WSL. Se o sistema interrompe uma thread que ainda tinha trabalho, a região paralela inteira atrasa. Com 44 threads, o OpenMP percebe que há mais threads que núcleos e reduz a espera ativa, e por isso o tempo volta a cair.

Teste que confirma a hipótese (matriz 100×100, média de 10 execuções):

| Threads | Padrão (espera ativa) | `OMP_WAIT_POLICY=passive` |
| --- | --- | --- |
| 8 | 0,50 ms | 0,44 ms |
| 12 | 1,35 ms | 0,60 ms |
| 14 | 7,77 ms | 0,77 ms |
| 16 | 2,59 ms | 0,82 ms |
| 21 | 8,05 ms | 1,02 ms |
| 22 | **19,62 ms** | **1,30 ms** |
| 44 | 2,05 ms | 1,94 ms |

Com `passive`, as threads dormem enquanto esperam. O tempo passa a crescer devagar e de forma previsível com o número de threads (o custo de criá-las), e os picos desaparecem. Com a configuração padrão, os picos mudam de lugar de uma rodada para outra (16 threads deu 10,8 ms no benchmark e 2,6 ms neste teste), o que reforça que vêm da disputa com o sistema operacional, e não do cálculo.

Na matriz 1000×1000, esse atraso de alguns milissegundos é pequeno perto dos ~100 ms da multiplicação, e por isso não aparece.

## Conclusões

1. Para matrizes grandes, o OpenMP reduz o tempo de 422 ms para 94 ms (4,47×) com 16 threads. O ganho é limitado pelo acesso à memória e pela mistura de núcleos rápidos e lentos, não só pela quantidade de núcleos.
2. Usar mais threads que núcleos não traz ganho, e já a partir de 16 threads o speedup para de crescer.
3. Para matrizes pequenas, o custo de criar e coordenar as threads é maior que o próprio cálculo, e a versão paralela é mais lenta (10×10) ou ganha muito pouco (100×100).
4. Ocupar quase todos os núcleos nem sempre é melhor: com a espera ativa padrão do OpenMP, interrupções do sistema operacional atrasam a região paralela inteira.
5. Com o mesmo número de threads, OpenMP e pthreads têm o mesmo desempenho. A vantagem do OpenMP é de programação: a mesma divisão em blocos contíguos de linhas sai de uma única diretiva, sem criar, dividir e esperar as threads manualmente, e o número de threads pode ser qualquer um.

## Observação sobre a variação dos tempos

Com 10 repetições por caso, o desvio padrão na matriz 1000×1000 ficou entre 4 e 23 ms (1% a 22% da média). A sequencial variou entre 401 ms e 466 ms. Isso é típico de notebooks, em que o processador muda de frequência por energia ou temperatura. Para medições mais estáveis, convém rodar com o carregador ligado e o Windows no modo de energia "Melhor desempenho".
