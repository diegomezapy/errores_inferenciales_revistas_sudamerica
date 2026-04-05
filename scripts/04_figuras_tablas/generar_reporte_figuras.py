"""
Genera tablas y figuras para el reporte de auditoria metodologica.
Salida: reporte_figuras/
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.ticker import MaxNLocator
from scipy.stats import chi2_contingency
from itertools import combinations
from pathlib import Path

BASE_DIR = Path(r"G:/Mi unidad/DECENA_FACEN/04_INVESTIGACION_REPO")
OUT_DIR = BASE_DIR / "reporte_figuras"
OUT_DIR.mkdir(exist_ok=True)

# ── Paleta de colores ──────────────────────────────────────────────────────────
COLOR_FF  = "#C0392B"   # rojo     - Falla fuerte
COLOR_DI  = "#E67E22"   # naranja  - Debilidad importante
COLOR_SFR = "#27AE60"   # verde    - Sin falla relevante

# ── Carga y preparacion de datos ──────────────────────────────────────────────
df = pd.read_csv(BASE_DIR / "base_auditoria_v41ntk.csv", sep=";", on_bad_lines="skip", encoding="utf-8-sig")
df["clasif_norm"] = df["clasificacion_inferencial"].str.strip().str.lower().replace({"falla forte": "falla fuerte"})

base = pd.read_csv(BASE_DIR / "BASE_FINAL_ANALISIS_2026-04-03.csv", sep=";", encoding="utf-8-sig")

nuevos = {
    "CSS_14_BRA_Legislativo_politica_comercial.pdf": "Ciencias sociales y humanidades",
    "CSS_17_CHI_Path_dependency_instituciones_politicas_reformas_electorales.pdf": "Ciencias sociales y humanidades",
    "CSS_18_CHI_Partidos_politicos_chilenos_cambio_estabilidad_electoral.pdf": "Ciencias sociales y humanidades",
    "CSS_19_CHI_Good_Politicians_Electoral_Success_Latin_America.pdf": "Ciencias sociales y humanidades",
    "CSS_20_CHI_Rendicion_cuentas_democracias_desarrollo.pdf": "Ciencias sociales y humanidades",
    "CSS_23_CHI_Cadena_causal_confianza_instituciones_politicas.pdf": "Ciencias sociales y humanidades",
    "CSS_24_CHI_Factores_desercion_retencion_educacion_superior.pdf": "Ciencias sociales y humanidades",
    "CSS_26_CHI_Prediccion_rendimiento_asignatura_regresion_logistica.pdf": "Ciencias sociales y humanidades",
    "CSS_27_CHI_Incidencia_direccion_escolar_compromiso_estudiantes_multiniv.pdf": "Ciencias sociales y humanidades",
    "CSS_28_CHI_Cambio_niveles_logros_aprendizaje_multinivel.pdf": "Ciencias sociales y humanidades",
}

cols_to_merge = ["nombre_archivo", "area", "macroarea_final"]
if "anio" not in df.columns:
    cols_to_merge.append("anio")

merged = df.merge(base[cols_to_merge].drop_duplicates("nombre_archivo"),
                  on="nombre_archivo", how="left")
for nombre, area in nuevos.items():
    merged.loc[merged["nombre_archivo"] == nombre, "area"] = area
    merged.loc[merged["nombre_archivo"] == nombre, "macroarea_final"] = area

aplicables = merged[merged["clasif_norm"] != "no aplica"].copy()
aplicables["area_efectiva"] = aplicables.apply(
    lambda r: r["area"] if (r["macroarea_final"] in ["SIN_AREA", None] or pd.isna(r["macroarea_final"])) else r["macroarea_final"], axis=1)
aplicables = aplicables[aplicables["area_efectiva"] != "SIN_AREA"].copy()
aplicables["anio"] = pd.to_numeric(aplicables["anio"], errors="coerce")

GRUPOS = {
    "Ciencias de la Salud":          "Cs. de la Salud",
    "Ciencias Naturales y Exactas":  "Cs. Naturales\ny Exactas",
    "Ciencias Agrarias y Ambientales": "Cs. Agrarias\ny Ambientales",
    "Psicologia":                    "Psicologia y\nCs. Sociales",
    "Ciencias sociales y humanidades": "Psicologia y\nCs. Sociales",
    "Ingenieria y Tecnologia":       "Ingenieria y\nTecnologia",
    "Educacion":                     "Educacion",
}
aplicables["grupo"] = aplicables["area_efectiva"].map(GRUPOS)
aplicables = aplicables[aplicables["grupo"].notna()]

ORDEN_GRUPOS = [
    "Cs. de la Salud",
    "Cs. Naturales\ny Exactas",
    "Cs. Agrarias\ny Ambientales",
    "Psicologia y\nCs. Sociales",
    "Ingenieria y\nTecnologia",
    "Educacion",
]
ORDEN_GRUPOS_CORTO = [
    "Cs. Salud", "Cs. Naturales", "Cs. Agrarias",
    "Psic./Cs. Soc.", "Ingenieria", "Educacion"
]

cols = ["falla fuerte", "debilidad importante", "sin falla relevante"]

pivot = aplicables.groupby("grupo")["clasif_norm"].value_counts().unstack(fill_value=0)
for c in cols:
    if c not in pivot.columns:
        pivot[c] = 0
pivot = pivot[cols].reindex(ORDEN_GRUPOS)
pivot["TOTAL"] = pivot.sum(axis=1)
pivot["%FF"]  = (pivot["falla fuerte"]         / pivot["TOTAL"] * 100).round(1)
pivot["%DI"]  = (pivot["debilidad importante"]  / pivot["TOTAL"] * 100).round(1)
pivot["%SFR"] = (pivot["sin falla relevante"]   / pivot["TOTAL"] * 100).round(1)

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 1 — Distribucion absoluta por grupo (barras apiladas)
# ═══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(11, 6))

x = np.arange(len(ORDEN_GRUPOS))
w = 0.55

b1 = ax.bar(x, pivot["falla fuerte"],         w, label="Falla fuerte",         color=COLOR_FF)
b2 = ax.bar(x, pivot["debilidad importante"],  w, bottom=pivot["falla fuerte"], label="Debilidad importante", color=COLOR_DI)
b3 = ax.bar(x, pivot["sin falla relevante"],   w,
            bottom=pivot["falla fuerte"] + pivot["debilidad importante"],
            label="Sin falla relevante", color=COLOR_SFR)

for i, g in enumerate(ORDEN_GRUPOS):
    ax.text(i, pivot.loc[g, "TOTAL"] + 1.5, "n=%d" % pivot.loc[g, "TOTAL"],
            ha="center", va="bottom", fontsize=9, fontweight="bold")

ax.set_xticks(x)
ax.set_xticklabels(ORDEN_GRUPOS_CORTO, fontsize=10)
ax.set_ylabel("Numero de articulos", fontsize=11)
ax.set_title("Distribucion de clasificaciones metodologicas por area disciplinar\n(n=628)", fontsize=12, fontweight="bold")
ax.legend(loc="upper right", fontsize=10)
ax.yaxis.set_major_locator(MaxNLocator(integer=True))
ax.set_ylim(0, 175)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()
plt.savefig(OUT_DIR / "fig1_distribucion_absoluta_por_area.png", dpi=150, bbox_inches="tight")
plt.close()
print("Fig 1 guardada.")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 2 — Distribucion porcentual por grupo (barras apiladas 100%)
# ═══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(11, 6))

pivot = pivot.sort_values("%FF", ascending=True)
ORDEN_GRUPOS_SORTED = pivot.index.tolist()
# map values for short labels
map_corto = dict(zip(ORDEN_GRUPOS, ORDEN_GRUPOS_CORTO))
ORDEN_GRUPOS_CORTO_SORTED = [map_corto[g] for g in ORDEN_GRUPOS_SORTED]
x = np.arange(len(ORDEN_GRUPOS_SORTED))

b1 = ax.bar(x, pivot["%FF"],  w, label="Falla fuerte",         color=COLOR_FF)
b2 = ax.bar(x, pivot["%DI"],  w, bottom=pivot["%FF"],           label="Debilidad importante", color=COLOR_DI)
b3 = ax.bar(x, pivot["%SFR"], w, bottom=pivot["%FF"]+pivot["%DI"], label="Sin falla relevante", color=COLOR_SFR)

for i, g in enumerate(ORDEN_GRUPOS_SORTED):
    ff  = pivot.loc[g, "%FF"]
    di  = pivot.loc[g, "%DI"]
    sfr = pivot.loc[g, "%SFR"]
    if ff > 5:
        ax.text(i, ff/2,           "%.0f%%" % ff,  ha="center", va="center", fontsize=9, color="white", fontweight="bold")
    if di > 5:
        ax.text(i, ff + di/2,      "%.0f%%" % di,  ha="center", va="center", fontsize=9, color="white", fontweight="bold")
    if sfr > 5:
        ax.text(i, ff + di + sfr/2, "%.0f%%" % sfr, ha="center", va="center", fontsize=9, color="white", fontweight="bold")
    ax.text(i, 102, "n=%d" % pivot.loc[g, "TOTAL"], ha="center", va="bottom", fontsize=8.5, color="#444")

ax.set_xticks(x)
ax.set_xticklabels(ORDEN_GRUPOS_CORTO_SORTED, fontsize=10)
ax.set_ylabel("Porcentaje (%)", fontsize=11)
ax.set_ylim(0, 112)
ax.set_title("Distribucion porcentual de clasificaciones metodologicas por area disciplinar\n(n=628)", fontsize=12, fontweight="bold")
ax.legend(loc="lower right", fontsize=10)
ax.spines["top"].set_visible(False)
ax.spines["right"].set_visible(False)

plt.tight_layout()
plt.savefig(OUT_DIR / "fig2_distribucion_porcentual_por_area.png", dpi=150, bbox_inches="tight")
plt.close()
print("Fig 2 guardada.")

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 3 — COMENTADA COMO SOLICITADO
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# FIGURA 4 — Distribucion general total (torta / dona)
# ═══════════════════════════════════════════════════════════════════════════════
totales = [pivot["falla fuerte"].sum(), pivot["debilidad importante"].sum(), pivot["sin falla relevante"].sum()]
etiquetas = ["Falla fuerte\n%d (%.1f%%)" % (totales[0], totales[0]/sum(totales)*100),
             "Debilidad importante\n%d (%.1f%%)" % (totales[1], totales[1]/sum(totales)*100),
             "Sin falla relevante\n%d (%.1f%%)" % (totales[2], totales[2]/sum(totales)*100)]

fig, ax = plt.subplots(figsize=(8, 6))
wedges, texts = ax.pie(totales, colors=[COLOR_FF, COLOR_DI, COLOR_SFR],
                       startangle=90, wedgeprops={"width": 0.55, "edgecolor": "white", "linewidth": 2})
ax.legend(wedges, etiquetas, loc="lower center", fontsize=11, frameon=False,
          bbox_to_anchor=(0.5, -0.12), ncol=1)
ax.set_title("Distribucion global de clasificaciones metodologicas\n(n=628)", fontsize=12, fontweight="bold")
plt.tight_layout()
plt.savefig(OUT_DIR / "fig4_distribucion_global.png", dpi=150, bbox_inches="tight")
plt.close()
print("Fig 4 guardada.")

# ═══════════════════════════════════════════════════════════════════════════════
# TABLA 1 — CSV para reporte
# ═══════════════════════════════════════════════════════════════════════════════
tabla = pivot[["falla fuerte","debilidad importante","sin falla relevante","TOTAL","%FF","%DI","%SFR"]].copy()
tabla.index = ORDEN_GRUPOS_CORTO
fila_total = pd.Series({
    "falla fuerte": pivot["falla fuerte"].sum(),
    "debilidad importante": pivot["debilidad importante"].sum(),
    "sin falla relevante": pivot["sin falla relevante"].sum(),
    "TOTAL": pivot["TOTAL"].sum(),
    "%FF":  round(pivot["falla fuerte"].sum() / pivot["TOTAL"].sum() * 100, 1),
    "%DI":  round(pivot["debilidad importante"].sum() / pivot["TOTAL"].sum() * 100, 1),
    "%SFR": round(pivot["sin falla relevante"].sum() / pivot["TOTAL"].sum() * 100, 1),
}, name="TOTAL")
tabla = pd.concat([tabla, fila_total.to_frame().T])
tabla.to_csv(OUT_DIR / "tabla1_distribucion_por_area.csv", sep=";", encoding="utf-8-sig")
print("Tabla 1 guardada.")

# COMENTADO: TABLA 2 — Por anio CSV
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
# TABLA 3 — Pairwise chi2
# ═══════════════════════════════════════════════════════════════════════════════
grupos_lista = ORDEN_GRUPOS
alpha_bonf = 0.05 / len(list(combinations(grupos_lista, 2)))
rows_chi2 = []
for g1, g2 in combinations(grupos_lista, 2):
    tabla_c = pivot.loc[[g1,g2], cols].values
    c2, pp, dof, _ = chi2_contingency(tabla_c)
    sig = "***" if pp < alpha_bonf else ("*" if pp < 0.05 else "ns")
    rows_chi2.append({"Grupo 1": g1, "Grupo 2": g2, "Chi2": round(c2,2), "p": round(pp,4), "sig": sig})
pd.DataFrame(rows_chi2).sort_values("p").to_csv(OUT_DIR / "tabla3_pairwise_chi2.csv", sep=";", index=False, encoding="utf-8-sig")
print("Tabla 3 guardada.")

print()
print("=" * 50)
print("Listo. Archivos en: reporte_figuras/")
print("  fig1_distribucion_absoluta_por_area.png")
print("  fig2_distribucion_porcentual_por_area.png")
print("  fig4_distribucion_global.png")
print("  tabla1_distribucion_por_area.csv")
print("  tabla2_distribucion_por_anio.csv")
print("  tabla3_pairwise_chi2.csv")
