"""
fig_simulacion_resultados.py
============================
Corre la simulación Monte Carlo con los parámetros exactos del artículo
y genera una figura de 3 paneles lista para publicación.

Salida: manuscrito/ARTICULO/tablasyfig/fig_simulacion_resultados.png
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from scipy.stats import gaussian_kde
from pathlib import Path

rng = np.random.default_rng(42)

# ── Parámetros del artículo ────────────────────────────────────────────────────
N   = 279_152       # tamaño poblacional
p   = 0.524         # proporción verdadera
R   = 4_000         # réplicas Monte Carlo
z   = 1.95996
d   = 0.05
n0  = z**2 * p * (1 - p) / d**2
n   = int(np.ceil(n0 / (1 + (n0 - 1) / N)))   # ≈ 384 con FPC

OUT = Path(
    r"G:\Mi unidad\DECENA_FACEN\03_TESIS\articulo_fallas_metodologicas"
    r"\manuscrito\ARTICULO\tablasyfig"
)
OUT.mkdir(parents=True, exist_ok=True)

print(f"Parámetros: N={N:,}, p={p}, n={n}, R={R:,}")

# ── Población finita ────────────────────────────────────────────────────────────
pop = rng.binomial(1, p, N).astype(float)

# ── Monte Carlo ─────────────────────────────────────────────────────────────────
est_srs   = np.empty(R)
ci_srs    = np.empty(R, dtype=bool)

est_strat = np.empty(R)
ci_strat  = np.empty(R, dtype=bool)

est_conv  = np.empty(R)

# Estratificación en 3 estratos por cuartil del índice (simula estrato geográfico)
# W_h ∝ tamaño del estrato
K = 3
strata_idx = np.array_split(np.arange(N), K)
Nh = [len(s) for s in strata_idx]
nh = [max(2, int(np.ceil(n * Nh[k] / N))) for k in range(K)]

# Pesos de conveniencia: unidades con y=1 son 3× más propensas a ser elegidas
prob_inc = np.where(pop == 1, 3.0, 1.0)
prob_inc = prob_inc / prob_inc.sum()

for r in range(R):
    # SRS
    idx = rng.choice(N, size=n, replace=False)
    s   = pop[idx]
    p_h = s.mean()
    fpc = 1 - n / N
    se  = np.sqrt(fpc * p_h * (1 - p_h) / n)
    est_srs[r] = p_h
    ci_srs[r]  = (p_h - z * se) <= p <= (p_h + z * se)

    # Estratificado proporcional
    parts = []
    for k in range(K):
        picked = rng.choice(strata_idx[k], size=nh[k], replace=False)
        parts.append(pop[picked])
    p_strat = sum(Nh[k] * parts[k].mean() / N for k in range(K))
    var_strat = sum((Nh[k]/N)**2 * (1 - nh[k]/Nh[k])
                    * parts[k].var(ddof=1) / nh[k] for k in range(K))
    se_strat = np.sqrt(var_strat)
    est_strat[r] = p_strat
    ci_strat[r]  = (p_strat - z * se_strat) <= p <= (p_strat + z * se_strat)

    # Conveniencia (no probabilístico)
    idx_c = rng.choice(N, size=n, replace=False, p=prob_inc)
    est_conv[r] = pop[idx_c].mean()

cov_srs   = ci_srs.mean()
cov_strat = ci_strat.mean()
rmse_srs   = np.sqrt(((est_srs   - p)**2).mean())
rmse_strat = np.sqrt(((est_strat - p)**2).mean())
rmse_conv  = np.sqrt(((est_conv  - p)**2).mean())
bias_srs   = 100 * (est_srs.mean()   - p) / p
bias_strat = 100 * (est_strat.mean() - p) / p
bias_conv  = 100 * (est_conv.mean()  - p) / p

print(f"SRS    : cov={cov_srs:.3f}  bias={bias_srs:+.2f}%  RMSE={rmse_srs:.4f}")
print(f"Strat  : cov={cov_strat:.3f}  bias={bias_strat:+.2f}%  RMSE={rmse_strat:.4f}")
print(f"Conv   : cov=N/A          bias={bias_conv:+.2f}%  RMSE={rmse_conv:.4f}")

# ── FIGURA ──────────────────────────────────────────────────────────────────────
BLUE  = "#2563EB"
GREEN = "#059669"
RED   = "#DC2626"
GRAY  = "#6B7280"
BG    = "#F8FAFC"
DARK  = "#1E293B"

plt.rcParams.update({
    "font.family":     "DejaVu Sans",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
    "axes.facecolor":     BG,
    "figure.facecolor":   "white",
    "axes.labelcolor":    DARK,
    "xtick.color":        DARK,
    "ytick.color":        DARK,
    "text.color":         DARK,
})

fig = plt.figure(figsize=(14, 10))
fig.patch.set_facecolor("white")
gs  = GridSpec(2, 2, figure=fig, hspace=0.40, wspace=0.32,
               left=0.07, right=0.97, top=0.90, bottom=0.08)

ax1 = fig.add_subplot(gs[0, :])   # top: distribuciones (ancho completo)
ax2 = fig.add_subplot(gs[1, 0])   # bottom-left: cobertura
ax3 = fig.add_subplot(gs[1, 1])   # bottom-right: RMSE + sesgo

# ── Panel A: distribuciones de densidad ────────────────────────────────────────
for est, color, label, lw in [
    (est_conv,  RED,   "Conveniencia (sesgado)", 2.5),
    (est_srs,   BLUE,  "MAS-SR",                 2.0),
    (est_strat, GREEN, "Estratificado proporcional", 2.0),
]:
    xs = np.linspace(est.min() - 0.02, est.max() + 0.02, 400)
    kde = gaussian_kde(est, bw_method=0.15)
    ys  = kde(xs)
    ax1.plot(xs, ys, color=color, lw=lw, label=label)
    ax1.fill_between(xs, ys, alpha=0.10, color=color)

ax1.axvline(p, color=DARK, lw=1.8, ls="--", label=f"p verdadero = {p}")
ax1.set_xlabel("Estimación de proporción $\\hat{p}$", fontsize=11)
ax1.set_ylabel("Densidad kernel", fontsize=11)
ax1.set_title(
    "Panel A — Distribución muestral del estimador de proporción "
    f"({R:,} réplicas Monte Carlo, $n={n}$, $N={N:,}$)",
    fontsize=12, fontweight="bold", pad=10, color=DARK
)
ax1.legend(fontsize=10, frameon=False, loc="upper left")
ax1.set_facecolor(BG)

# Anota el sesgo de conveniencia
mu_conv = est_conv.mean()
ax1.annotate(
    f" Sesgo\n {bias_conv:+.1f}%",
    xy=(mu_conv, 0.5),
    xycoords=("data", "axes fraction"),
    fontsize=9, color=RED, fontstyle="italic",
)

# ── Panel B: cobertura ─────────────────────────────────────────────────────────
designs  = ["MAS-SR", "Estratificado\nproporcional", "Conveniencia"]
coverages = [cov_srs, cov_strat, np.nan]
colors_b  = [BLUE, GREEN, RED]
bars = ax2.bar(designs, [c if not np.isnan(c) else 0 for c in coverages],
               color=colors_b, width=0.5, zorder=3, alpha=0.85)

# Barra de conveniencia con patrón
bars[2].set_hatch("///")
bars[2].set_edgecolor(RED)
bars[2].set_facecolor("#FEE2E2")

ax2.axhline(0.95, color=DARK, lw=1.6, ls="--", zorder=4,
            label="Nominal 95 %")
ax2.set_ylim(0.80, 1.01)
ax2.set_yticks([0.80, 0.85, 0.90, 0.95, 1.00])
ax2.set_yticklabels(["80 %", "85 %", "90 %", "95 %", "100 %"])
ax2.set_ylabel("Cobertura empírica", fontsize=11)
ax2.set_title("Panel B — Cobertura del IC 95 %", fontsize=12,
              fontweight="bold", color=DARK)
ax2.legend(fontsize=9, frameon=False)
ax2.set_facecolor(BG)

for bar, cov in zip(bars, coverages):
    if not np.isnan(cov):
        ax2.text(bar.get_x() + bar.get_width()/2, cov + 0.002,
                 f"{cov:.1%}", ha="center", va="bottom", fontsize=10,
                 fontweight="bold", color=DARK)
    else:
        ax2.text(bar.get_x() + bar.get_width()/2, 0.82,
                 "No\naplicable", ha="center", va="bottom", fontsize=9,
                 color=RED, fontstyle="italic")

# ── Panel C: sesgo y RMSE (lollipop doble) ────────────────────────────────────
xs_labels = ["MAS-SR", "Estratificado\nproporcional", "Conveniencia"]
xs_pos    = np.array([0, 1, 2])
biases    = [bias_srs, bias_strat, bias_conv]
rmses_pct = [rmse_srs * 100, rmse_strat * 100, rmse_conv * 100]
colors_c  = [BLUE, GREEN, RED]

# Sesgo
for x, b, c in zip(xs_pos - 0.12, biases, colors_c):
    ax3.vlines(x, 0, b, colors=c, lw=2.5)
    ax3.scatter(x, b, s=80, color=c, zorder=5)

# RMSE (escala secundaria)
ax3b = ax3.twinx()
for x, r, c in zip(xs_pos + 0.12, rmses_pct, colors_c):
    ax3b.vlines(x, 0, r, colors=c, lw=2.5, ls=":")
    ax3b.scatter(x, r, s=80, color=c, marker="D", zorder=5)

ax3.axhline(0, color=DARK, lw=0.8, alpha=0.5)
ax3.set_xticks(xs_pos)
ax3.set_xticklabels(xs_labels, fontsize=9)
ax3.set_ylabel("Sesgo relativo (%)", fontsize=11, color=DARK)
ax3b.set_ylabel("RMSE × 100", fontsize=11, color=GRAY)
ax3b.tick_params(axis="y", colors=GRAY)
ax3.set_title("Panel C — Sesgo relativo y RMSE (proporción)",
              fontsize=12, fontweight="bold", color=DARK)
ax3.set_facecolor(BG)

leg1 = mpatches.Patch(color=DARK,   label="● Sesgo relativo (%)")
leg2 = mpatches.Patch(color=GRAY,   label="◆ RMSE × 100 (punteado)")
ax3.legend(handles=[leg1, leg2], fontsize=9, frameon=False, loc="upper left")

# Anota los valores
for x, b, r in zip(xs_pos, biases, rmses_pct):
    ax3.text(x - 0.12, b + (0.04 if b >= 0 else -0.12),
             f"{b:+.2f}%", ha="center", fontsize=8, color=DARK)
    ax3b.text(x + 0.12, r + 0.05,
              f"{r:.2f}", ha="center", fontsize=8, color=GRAY)

# ── Título general ─────────────────────────────────────────────────────────────
fig.suptitle(
    "Resultados de la simulación Monte Carlo — "
    "Diseños probabilísticos vs. muestreo por conveniencia",
    fontsize=13, fontweight="bold", y=0.97, color=DARK
)

out_path = OUT / "fig_simulacion_resultados.png"
plt.savefig(out_path, dpi=300, bbox_inches="tight", facecolor="white")
plt.close()
print(f"\n✓ Figura guardada: {out_path}")
