#!/usr/bin/env python3
"""Resume resultados/openmp.csv e gera tabela e graficos da parte 2 (OpenMP).

Uso (a partir da raiz do repositorio):
    python3 scripts/graficos_openmp.py

Gera:
    resultados/openmp_resumo.csv     media dos tempos por caso, speedup e eficiencia
    resultados/openmp_tempo.png      tempo medio x numero de threads
    resultados/openmp_speedup.png    speedup x numero de threads

Speedup e calculado de duas formas:
    speedup_seq = tempo da sequencial / tempo da versao paralela
    speedup_1t  = tempo do OpenMP com 1 thread / tempo do OpenMP com N threads
As tres versoes usam o mesmo laco (acumulador local), entao speedup_seq
mede so o ganho do paralelismo. O speedup_1t mostra, alem disso, o custo
do proprio OpenMP com 1 thread.
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
PARALELAS = ["pthreads", "openmp"]


def le_nucleos():
    """Nucleos da maquina que rodou o benchmark (gravados pelo .sh)."""
    try:
        with open(os.path.join(PASTA, "nucleos.txt")) as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return os.cpu_count()


NUCLEOS = le_nucleos()

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
threads = {v: sorted({n for (w, _, n) in tempos if w == v}) for v in PARALELAS}


def desvio(amostras):
    return stdev(amostras) if len(amostras) > 1 else 0


linhas = []
for tam in tamanhos:
    seq = mean(tempos[("sequencial", tam, 1)])
    um = mean(tempos[("openmp", tam, 1)]) if ("openmp", tam, 1) in tempos else None
    linhas.append({
        "versao": "sequencial", "tamanho": tam, "threads": 1,
        "tempo_medio_ms": seq / 1000,
        "desvio_ms": desvio(tempos[("sequencial", tam, 1)]) / 1000,
        "speedup_seq": 1.0, "eficiencia_seq": 1.0,
        "speedup_1t": "", "eficiencia_1t": "",
    })
    for versao in PARALELAS:
        for n in threads[versao]:
            amostras = tempos[(versao, tam, n)]
            t = mean(amostras)
            usa_1t = versao == "openmp" and um is not None
            linhas.append({
                "versao": versao, "tamanho": tam, "threads": n,
                "tempo_medio_ms": t / 1000,
                "desvio_ms": desvio(amostras) / 1000,
                "speedup_seq": seq / t,
                "eficiencia_seq": seq / t / n,
                "speedup_1t": um / t if usa_1t else "",
                "eficiencia_1t": um / t / n if usa_1t else "",
            })

campos = ["versao", "tamanho", "threads", "tempo_medio_ms", "desvio_ms",
          "speedup_seq", "eficiencia_seq", "speedup_1t", "eficiencia_1t"]
with open(os.path.join(PASTA, "openmp_resumo.csv"), "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=campos)
    w.writeheader()
    for l in linhas:
        w.writerow({k: (f"{v:.3f}" if isinstance(v, float) else v)
                    for k, v in l.items()})

# Tabela no terminal
print(f"\nNucleos logicos: {NUCLEOS}\n")
print(f"{'versao':<11}{'tamanho':>8}{'threads':>8}{'tempo (ms)':>13}"
      f"{'speedup_seq':>13}{'eficiencia':>12}{'speedup_1t':>12}")
for l in linhas:
    s1 = f"{l['speedup_1t']:.2f}" if l["speedup_1t"] != "" else "-"
    print(f"{l['versao']:<11}{l['tamanho']:>8}{l['threads']:>8}"
          f"{l['tempo_medio_ms']:>13.3f}{l['speedup_seq']:>13.2f}"
          f"{l['eficiencia_seq']:>12.0%}{s1:>12}")


def marca_nucleos(ax, xs):
    if NUCLEOS and min(xs) <= NUCLEOS <= max(xs):
        ax.axvline(NUCLEOS, color="gray", linestyle=":", linewidth=1)
        ax.text(NUCLEOS, ax.get_ylim()[1], f" {NUCLEOS} núcleos",
                color="gray", va="top", fontsize=9)


def eixo_threads(ax, xs):
    ax.set_xlabel("Número de threads")
    ax.set_xscale("log", base=2)
    ax.set_xticks(xs, [str(n) for n in xs])
    ax.grid(alpha=0.3)


ESTILO = {"openmp": dict(marker="o", label="OpenMP"),
          "pthreads": dict(marker="s", label="pthreads")}
todas = sorted(set(threads["openmp"]) | set(threads["pthreads"]))

# Grafico 1: tempo medio x threads (um subgrafico por tamanho, escalas diferentes)
fig, eixos = plt.subplots(1, len(tamanhos), figsize=(5 * len(tamanhos), 4))
if len(tamanhos) == 1:
    eixos = [eixos]
for ax, tam in zip(eixos, tamanhos):
    for versao in PARALELAS:
        xs = threads[versao]
        if xs:
            ax.plot(xs, [mean(tempos[(versao, tam, n)]) / 1000 for n in xs],
                    **ESTILO[versao])
    ax.axhline(mean(tempos[("sequencial", tam, 1)]) / 1000, color="red",
               linestyle="--", label="Sequencial")
    ax.set_title(f"Matriz {tam}x{tam}")
    ax.set_ylabel("Tempo médio (ms)")
    eixo_threads(ax, todas)
    marca_nucleos(ax, todas)
    ax.legend()
fig.suptitle("Tempo de execução")
fig.tight_layout()
fig.savefig(os.path.join(PASTA, "openmp_tempo.png"), dpi=150)

# Grafico 2: speedup em relacao a versao sequencial
fig, ax = plt.subplots(figsize=(6.5, 4.8))
cores = plt.rcParams["axes.prop_cycle"].by_key()["color"]
for cor, tam in zip(cores, tamanhos):
    seq = mean(tempos[("sequencial", tam, 1)])
    for versao, estilo in (("openmp", "-"), ("pthreads", ":")):
        xs = threads[versao]
        if xs:
            ax.plot(xs, [seq / mean(tempos[(versao, tam, n)]) for n in xs],
                    color=cor, linestyle=estilo, marker=ESTILO[versao]["marker"],
                    label=f"{ESTILO[versao]['label']} {tam}x{tam}")
ax.plot(todas, [min(n, NUCLEOS or n) for n in todas], color="gray",
        linestyle="--", label="Ideal (limitado pelos núcleos)")
ax.set_title("Speedup em relação à versão sequencial")
ax.set_ylabel("Speedup")
eixo_threads(ax, todas)
marca_nucleos(ax, todas)
ax.legend(fontsize=8)
fig.tight_layout()
fig.savefig(os.path.join(PASTA, "openmp_speedup.png"), dpi=150)

print(f"\nArquivos gerados em {PASTA}/: openmp_resumo.csv, openmp_tempo.png,"
      " openmp_speedup.png")
