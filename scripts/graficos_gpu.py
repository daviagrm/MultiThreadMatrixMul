#!/usr/bin/env python3
"""Resume os resultados das GPUs (CUDA e OpenCL) e compara com a CPU.

Uso (a partir da raiz do repositorio, depois dos benchmarks):
    python3 scripts/graficos_gpu.py

Le (os arquivos de GPU sao opcionais; basta existir um deles):
    resultados/openmp.csv     scripts/benchmark_openmp.sh  (CPU, obrigatorio)
    resultados/cuda.csv       scripts/benchmark_cuda.sh    (so GPU NVIDIA)
    resultados/opencl.csv     scripts/benchmark_opencl.sh  (GPU AMD, NVIDIA ou Intel)

Gera:
    resultados/gpu_resumo.csv     media por GPU, tamanho e tamanho de bloco
    resultados/comparacao.csv     melhor tempo de cada versao, por tamanho
    resultados/gpu_blocos.png     tempo de cada GPU dividido em kernel e copias
    resultados/comparacao.png     CPU (sequencial, pthreads, OpenMP) x GPUs
"""

import csv
import os
import re
import sys
from collections import defaultdict
from statistics import mean, stdev

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PASTA = "resultados"
ARQUIVOS_GPU = [("CUDA", "cuda.csv"), ("OpenCL", "opencl.csv")]

# Paleta categorica em ordem fixa: CPU nas 3 primeiras cores, GPUs nas seguintes
PALETA = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4",
          "#008300", "#6250d6", "#e34948"]
TINTA = "#3d3d3a"   # texto secundario
GRADE = "#d9d8d2"   # linhas de grade recessivas
FUNDO = "white"

plt.rcParams.update({
    "axes.edgecolor": GRADE, "axes.labelcolor": TINTA, "xtick.color": TINTA,
    "ytick.color": TINTA, "axes.titlecolor": "#1a1a19", "font.size": 10,
})


def desvio(xs):
    """Desvio padrao amostral (0 quando ha uma amostra so)."""
    return stdev(xs) if len(xs) > 1 else 0


def nome_curto(gpu):
    """'NVIDIA GeForce RTX 4060 Laptop GPU' -> 'RTX 4060 Laptop'."""
    for lixo in ("NVIDIA", "GeForce", "AMD", "Radeon(TM)", "Intel(R)", "(TM)", "(R)", "GPU"):
        gpu = gpu.replace(lixo, "")
    return re.sub(r"\s+", " ", gpu).strip() or "GPU"


# ---- CPU
cpu = defaultdict(list)          # (versao, tamanho, threads) -> [us]
somas = defaultdict(set)         # tamanho -> somas encontradas (todas as versoes)
with open(os.path.join(PASTA, "openmp.csv"), newline="", encoding="utf-8") as f:
    for l in csv.DictReader(f):
        cpu[(l["versao"], int(l["tamanho"]), int(l["threads"]))].append(int(l["tempo_us"]))
        somas[int(l["tamanho"])].add(l["soma"])

# ---- GPUs: cada combinacao (API, GPU) vira uma "configuracao"
total = defaultdict(list)        # (config, tamanho, lado) -> [us]
kernel = defaultdict(list)
configs = []                     # em ordem de aparicao: CUDA primeiro, depois OpenCL
for api, arquivo in ARQUIVOS_GPU:
    caminho = os.path.join(PASTA, arquivo)
    if not os.path.exists(caminho):
        print(f"Aviso: {caminho} nao encontrado; {api} fica fora da comparacao")
        continue
    with open(caminho, newline="", encoding="utf-8") as f:
        for l in csv.DictReader(f):
            cfg = f"{api} ({nome_curto(l['gpu'])})"
            if cfg not in configs:
                configs.append(cfg)
            chave = (cfg, int(l["tamanho"]), int(l["lado"]))
            total[chave].append(int(l["tempo_total_us"]))
            kernel[chave].append(int(l["tempo_kernel_us"]))
            somas[int(l["tamanho"])].add(l["soma"])
if not configs:
    sys.exit("Nenhum resultado de GPU encontrado: rode benchmark_cuda.sh ou benchmark_opencl.sh")

for tam, s in sorted(somas.items()):
    estado = "OK" if len(s) == 1 else "DIFERENTES, verifique o codigo!"
    print(f"Soma de verificacao {tam}x{tam} (CPU e GPUs): {estado}")

tamanhos = sorted({t for (_, t, _) in total})
lados = sorted({b for (_, _, b) in total})


def lados_de(cfg, tam):
    """Tamanhos de bloco medidos (algumas GPUs nao aceitam 32x32)."""
    return [b for b in lados if (cfg, tam, b) in total]


# ---- resumo por GPU e tamanho de bloco
with open(os.path.join(PASTA, "gpu_resumo.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["configuracao", "tamanho", "lado", "threads_por_bloco", "total_ms",
                "desvio_total_ms", "kernel_ms", "desvio_kernel_ms", "copias_ms"])
    print(f"\n{'configuracao':<30}{'tamanho':>8}{'bloco':>8}{'total (ms)':>12}"
          f"{'kernel (ms)':>13}{'copias (ms)':>13}")
    for cfg in configs:
        for tam in tamanhos:
            for b in lados_de(cfg, tam):
                t, k = total[(cfg, tam, b)], kernel[(cfg, tam, b)]
                w.writerow([cfg, tam, b, b * b, f"{mean(t) / 1000:.3f}",
                            f"{desvio(t) / 1000:.3f}", f"{mean(k) / 1000:.3f}",
                            f"{desvio(k) / 1000:.3f}", f"{(mean(t) - mean(k)) / 1000:.3f}"])
                print(f"{cfg:<30}{tam:>8}{f'{b}x{b}':>8}{mean(t) / 1000:>12.3f}"
                      f"{mean(k) / 1000:>13.3f}{(mean(t) - mean(k)) / 1000:>13.3f}")


# ---- melhor configuracao de cada versao, por tamanho
def threads_txt(n):
    return f"{n} thread" + ("s" if n > 1 else "")


def melhor_cpu(versao, tam):
    return min((mean(v), n) for (ver, t, n), v in cpu.items() if ver == versao and t == tam)


def melhor_gpu(dados, cfg, tam):
    return min((mean(dados[(cfg, tam, b)]), b) for b in lados_de(cfg, tam))


comparacao = []  # (tamanho, versao, tempo_ms, kernel_ms ou None, configuracao)
for tam in tamanhos:
    for versao, rotulo in (("sequencial", "Sequencial"), ("pthreads", "pthreads"),
                           ("openmp", "OpenMP")):
        us, n = melhor_cpu(versao, tam)
        comparacao.append((tam, rotulo, us / 1000, None, threads_txt(n)))
    for cfg in configs:
        us, b = melhor_gpu(total, cfg, tam)
        k, _ = melhor_gpu(kernel, cfg, tam)
        comparacao.append((tam, cfg, us / 1000, k / 1000, f"blocos {b}x{b}"))

with open(os.path.join(PASTA, "comparacao.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["tamanho", "versao", "melhor_tempo_ms", "melhor_kernel_ms",
                "configuracao", "speedup_seq"])
    print(f"\n{'tamanho':>8}  {'versao':<30}{'tempo (ms)':>12}{'kernel (ms)':>13}"
          f"{'speedup':>10}  configuracao")
    for tam, versao, ms, k, cfg in comparacao:
        seq = next(m for t, v, m, _, _ in comparacao if t == tam and v == "Sequencial")
        w.writerow([tam, versao, f"{ms:.4f}", "" if k is None else f"{k:.4f}", cfg,
                    f"{seq / ms:.3f}"])
        ktxt = "-" if k is None else f"{k:.4f}"
        print(f"{tam:>8}  {versao:<30}{ms:>12.4f}{ktxt:>13}{seq / ms:>10.2f}  {cfg}")

versoes = ["Sequencial", "pthreads", "OpenMP"] + configs
COR = dict(zip(versoes, PALETA))

# ---- Grafico 1: cada GPU (colunas) x tamanho (linhas), kernel + copias por bloco
fig, eixos = plt.subplots(len(tamanhos), len(configs), squeeze=False,
                          figsize=(4 * len(configs), 3 * len(tamanhos)))
for lin, tam in enumerate(tamanhos):
    for col, cfg in enumerate(configs):
        ax = eixos[lin][col]
        bs = lados_de(cfg, tam)
        xs = [lados.index(b) for b in bs]   # posicao fixa de cada bloco
        k = [mean(kernel[(cfg, tam, b)]) / 1000 for b in bs]
        c = [(mean(total[(cfg, tam, b)]) - mean(kernel[(cfg, tam, b)])) / 1000 for b in bs]
        ax.bar(xs, k, width=0.55, color=COR[cfg], edgecolor=FUNDO, linewidth=2, zorder=3)
        ax.bar(xs, c, width=0.55, bottom=k, color=COR[cfg], alpha=0.35,
               edgecolor=FUNDO, linewidth=2, zorder=3)
        for x, a, b in zip(xs, k, c):
            ax.text(x, a + b, f"{a + b:.2f}", ha="center", va="bottom", fontsize=8, color=TINTA)
        ax.set_xticks(range(len(lados)), [f"{b}x{b}" for b in lados])
        ax.set_xlim(-0.6, len(lados) - 0.4)
        ax.margins(y=0.18)
        for x, b in enumerate(lados):
            if b not in bs:   # bloco grande demais para esta GPU
                ax.text(x, ax.get_ylim()[1] * 0.05, "não\nsuportado", ha="center",
                        va="bottom", fontsize=8, color=TINTA, style="italic")
        ax.grid(axis="y", color=GRADE, linewidth=0.8, zorder=0)
        ax.spines[["top", "right"]].set_visible(False)
        if lin == 0:
            ax.set_title(cfg, fontsize=10)
        if col == 0:
            ax.set_ylabel(f"{tam}x{tam}\ntempo médio (ms)")
        if lin == len(tamanhos) - 1:
            ax.set_xlabel("Bloco de threads")
# legenda neutra: parte cheia = kernel, parte clara = copias
from matplotlib.patches import Patch  # noqa: E402
fig.legend(handles=[Patch(color=TINTA, label="Kernel (cálculo na GPU)"),
                    Patch(color=TINTA, alpha=0.35, label="Cópias CPU↔GPU")],
           frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 0.955))
fig.suptitle("GPU: tempo por tamanho de bloco (escalas diferentes em cada gráfico)")
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig(os.path.join(PASTA, "gpu_blocos.png"), dpi=150, facecolor=FUNDO)

# ---- Grafico 2: melhor tempo de cada versao, com copias (escala log, um eixo)
largura = 0.8 / len(versoes)
fig, ax = plt.subplots(figsize=(10, 5))
for i, versao in enumerate(versoes):
    ys = [next(m for t, v, m, _, _ in comparacao if t == tam and v == versao) for tam in tamanhos]
    pos = [g + (i - (len(versoes) - 1) / 2) * largura for g in range(len(tamanhos))]
    ax.bar(pos, ys, width=largura, color=COR[versao], label=versao,
           edgecolor=FUNDO, linewidth=2, zorder=3)
    for x, y in zip(pos, ys):
        rotulo = f"{y:.1f}" if y >= 1 else f"{y:.2g}"
        ax.text(x, y * 1.15, rotulo, ha="center", va="bottom", fontsize=7,
                color=TINTA, rotation=90)
ax.set_yscale("log")
ax.set_xticks(range(len(tamanhos)), [f"{t}x{t}" for t in tamanhos])
ax.set_xlabel("Tamanho da matriz")
ax.set_ylabel("Melhor tempo médio (ms, escala log)")
ax.set_title("Melhor tempo de cada versão (GPU incluindo as cópias)")
ax.set_ylim(top=ax.get_ylim()[1] * 30)
ax.grid(axis="y", color=GRADE, linewidth=0.8, zorder=0)
ax.spines[["top", "right"]].set_visible(False)
ax.legend(frameon=False, ncol=3, fontsize=8, loc="upper left")
fig.tight_layout()
fig.savefig(os.path.join(PASTA, "comparacao.png"), dpi=150, facecolor=FUNDO)

print(f"\nArquivos gerados em {PASTA}/: gpu_resumo.csv, comparacao.csv,"
      " gpu_blocos.png, comparacao.png")
