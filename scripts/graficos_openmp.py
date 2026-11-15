#!/usr/bin/env python3
"""Resume resultados/openmp.csv e gera tabela e graficos da parte 2 (OpenMP).

Uso (a partir da raiz do repositorio):
    python3 scripts/graficos_openmp.py

Gera:
    resultados/openmp_resumo.csv     media dos tempos por caso, speedup e eficiencia
    resultados/openmp_tempo.png      tempo medio x numero de threads
    resultados/openmp_speedup.png    speedup x numero de threads

Speedup e calculado de duas formas:
    speedup_seq = tempo da sequencial / tempo do OpenMP
    speedup_1t  = tempo do OpenMP com 1 thread / tempo do OpenMP com N threads
O speedup_1t compara o mesmo codigo com mais ou menos threads e por isso
mostra melhor o ganho do paralelismo em si.
"""

import csv
import os
from collections import defaultdict
from statistics import mean, stdev

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ENTRADA = "resultados/openmp.csv"
PASTA = "resultados"
NUCLEOS = os.cpu_count()

tempos = defaultdict(list)  # (versao, tamanho, threads) -> [tempo_us, ...]
somas = defaultdict(set)    # tamanho -> somas de verificacao encontradas
with open(ENTRADA, newline="") as f:
    for linha in csv.DictReader(f):
        chave = (linha["versao"], int(linha["tamanho"]), int(linha["threads"]))
        tempos[chave].append(int(linha["tempo_us"]))
        somas[int(linha["tamanho"])].add(linha["soma"])

# Conferencia: todas as versoes devem dar a mesma soma para cada tamanho
for tam, s in sorted(somas.items()):
    estado = "OK" if len(s) == 1 else "DIFERENTES, verifique o codigo!"
    print(f"Soma de verificacao {tam}x{tam}: {estado}")

tamanhos = sorted({t for (_, t, _) in tempos})
threads = sorted({n for (v, _, n) in tempos if v == "openmp"})

linhas = []
for tam in tamanhos:
    seq = mean(tempos[("sequencial", tam, 1)])
    um = mean(tempos[("openmp", tam, 1)])
    linhas.append({
        "versao": "sequencial", "tamanho": tam, "threads": 1,
        "tempo_medio_ms": seq / 1000,
        "desvio_ms": (stdev(tempos[("sequencial", tam, 1)]) if len(tempos[("sequencial", tam, 1)]) > 1 else 0) / 1000,
        "speedup_seq": 1.0, "speedup_1t": "", "eficiencia_1t": "",
    })
    for n in threads:
        amostras = tempos[("openmp", tam, n)]
        t = mean(amostras)
        linhas.append({
            "versao": "openmp", "tamanho": tam, "threads": n,
            "tempo_medio_ms": t / 1000,
            "desvio_ms": (stdev(amostras) if len(amostras) > 1 else 0) / 1000,
            "speedup_seq": seq / t,
            "speedup_1t": um / t,
            "eficiencia_1t": um / t / n,
        })

campos = ["versao", "tamanho", "threads", "tempo_medio_ms", "desvio_ms",
          "speedup_seq", "speedup_1t", "eficiencia_1t"]
with open(os.path.join(PASTA, "openmp_resumo.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=campos)
    w.writeheader()
    for l in linhas:
        w.writerow({k: (f"{v:.3f}" if isinstance(v, float) else v)
                    for k, v in l.items()})

# Tabela no terminal
print(f"\nNucleos logicos: {NUCLEOS}\n")
print(f"{'versao':<11}{'tamanho':>8}{'threads':>8}{'tempo (ms)':>13}"
      f"{'speedup_seq':>13}{'speedup_1t':>12}{'eficiencia':>12}")
for l in linhas:
    s1 = f"{l['speedup_1t']:.2f}" if l["speedup_1t"] != "" else "-"
    ef = f"{l['eficiencia_1t']:.0%}" if l["eficiencia_1t"] != "" else "-"
    print(f"{l['versao']:<11}{l['tamanho']:>8}{l['threads']:>8}"
          f"{l['tempo_medio_ms']:>13.3f}{l['speedup_seq']:>13.2f}{s1:>12}{ef:>12}")


def marca_nucleos(ax):
    if NUCLEOS:
        ax.axvline(NUCLEOS, color="gray", linestyle=":", linewidth=1)
        ax.text(NUCLEOS, ax.get_ylim()[1], f" {NUCLEOS} núcleos",
                color="gray", va="top", fontsize=9)


# Grafico 1: tempo medio x threads (um subgrafico por tamanho, escalas diferentes)
fig, eixos = plt.subplots(1, len(tamanhos), figsize=(5 * len(tamanhos), 4))
if len(tamanhos) == 1:
    eixos = [eixos]
for ax, tam in zip(eixos, tamanhos):
    ys = [mean(tempos[("openmp", tam, n)]) / 1000 for n in threads]
    ax.plot(threads, ys, marker="o", label="OpenMP")
    ax.axhline(mean(tempos[("sequencial", tam, 1)]) / 1000, color="red",
               linestyle="--", label="Sequencial")
    ax.set_title(f"Matriz {tam}x{tam}")
    ax.set_xlabel("Número de threads")
    ax.set_ylabel("Tempo médio (ms)")
    ax.set_xscale("log", base=2)
    ax.set_xticks(threads, [str(n) for n in threads])
    ax.grid(alpha=0.3)
    marca_nucleos(ax)
    ax.legend()
fig.suptitle("OpenMP: tempo de execução")
fig.tight_layout()
fig.savefig(os.path.join(PASTA, "openmp_tempo.png"), dpi=150)

# Grafico 2: speedup em relacao ao OpenMP com 1 thread
fig, ax = plt.subplots(figsize=(6, 4.5))
for tam in tamanhos:
    um = mean(tempos[("openmp", tam, 1)])
    ax.plot(threads, [um / mean(tempos[("openmp", tam, n)]) for n in threads],
            marker="o", label=f"{tam}x{tam}")
ax.plot(threads, [min(n, NUCLEOS or n) for n in threads], color="gray",
        linestyle="--", label="Ideal (limitado pelos núcleos)")
ax.set_title("OpenMP: speedup em relação a 1 thread")
ax.set_xlabel("Número de threads")
ax.set_ylabel("Speedup")
ax.set_xscale("log", base=2)
ax.set_xticks(threads, [str(n) for n in threads])
ax.grid(alpha=0.3)
marca_nucleos(ax)
ax.legend()
fig.tight_layout()
fig.savefig(os.path.join(PASTA, "openmp_speedup.png"), dpi=150)

print(f"\nArquivos gerados em {PASTA}/: openmp_resumo.csv, openmp_tempo.png,"
      " openmp_speedup.png")
