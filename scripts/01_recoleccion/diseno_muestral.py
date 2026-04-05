"""
Diseño muestral estratificado para estimar fallas metodológicas
en inferencia estadística en revistas de América del Sur.

Dos métricas:
  M1 - Proporción de artículos con fallas dentro de una revista
       (nivel artículo, estimador de proporción intra-revista)
  M2 - Proporción de revistas con al menos un artículo con falla
       (nivel revista, estimador binario)

Diseño: Muestreo Estratificado Proporcional (MEP)
  - Estratos : macroáreas temáticas
  - Unidad primaria de muestreo (UPM) : revista
  - Unidad secundaria (USM) : artículos dentro de cada revista seleccionada
"""

import pandas as pd
import numpy as np
from math import ceil

INPUT_CSV      = "g:/Mi unidad/DECENA_FACEN/04_INVESTIGACION_REPO/revistas_clasificadas.csv"
OUTPUT_MUESTRA = "g:/Mi unidad/DECENA_FACEN/04_INVESTIGACION_REPO/muestra_revistas.csv"
OUTPUT_EXCEL   = "g:/Mi unidad/DECENA_FACEN/04_INVESTIGACION_REPO/muestra_revistas.xlsx"

# ---------------------------------------------------------------------------
# Parámetros estadísticos del diseño
# ---------------------------------------------------------------------------

Z     = 1.96      # nivel de confianza 95%
E_M2  = 0.05      # error máximo aceptable para M2 (±5 puntos porcentuales)
E_M1  = 0.08      # error máximo aceptable para M1 intra-revista (±8 pp)
p_M2  = 0.50      # proporción esperada de revistas con fallas (conservador = 0.5)
p_M1  = 0.30      # proporción esperada de artículos con fallas (estimado)
ICC   = 0.10      # coeficiente de correlación intraclase (artículos dentro de revista)
k     = 10        # artículos a revisar por revista (muestra de artículos)

STRATA_MINIMO = 5  # mínimo de revistas por estrato (aunque el cálculo dé menos)

# Estratos excluidos por baja densidad inferencial real
STRATA_EXCLUIR = {"Derecho y Ciencias Juridicas", "Humanidades"}

# ---------------------------------------------------------------------------
# Fórmulas
# ---------------------------------------------------------------------------

def n_simple(z, p, e):
    """Tamaño muestral sin corrección por población finita."""
    return (z**2 * p * (1 - p)) / (e**2)


def fpc(n0, N):
    """Corrección por población finita."""
    return ceil(n0 / (1 + (n0 - 1) / N))


def deff(icc, k):
    """Efecto de diseño para muestreo en conglomerados (2da etapa)."""
    return 1 + (k - 1) * icc


def n_m1_revista(z, p, e, icc, k):
    """
    Número de revistas necesarias para estimar M1 con diseño en 2 etapas.
    n_rev = DEFF * n_simple / k   (revistas a visitar)
    Derivado de: V(p̂) = DEFF * p(1-p) / (m * k)
    """
    d = deff(icc, k)
    n_art_total = d * n_simple(z, p, e)  # artículos totales equivalentes
    return ceil(n_art_total / k)


# ---------------------------------------------------------------------------
# Carga de datos
# ---------------------------------------------------------------------------

df = pd.read_csv(INPUT_CSV, sep=";", encoding="utf-8-sig")
df_inf = df[df["metodologia"].isin(
    ["Inferencia Estadística", "Experimental + Estadística", "Experimental"]
)].copy()

df_inf = df_inf[~df_inf["macroarea"].isin(STRATA_EXCLUIR)]
N_total = len(df_inf)

# ---------------------------------------------------------------------------
# Cálculo de tamaños muestrales por estrato
# ---------------------------------------------------------------------------

# Tamaño global para M2 (nivel revista)
n0_M2  = n_simple(Z, p_M2, E_M2)
n_M2   = fpc(n0_M2, N_total)

# Tamaño global para M1 (nivel artículo → convertido a revistas)
n_M1_rev = n_m1_revista(Z, p_M1, E_M1, ICC, k)
n_M1_fpc = fpc(n_M1_rev, N_total)

n_global = max(n_M2, n_M1_fpc)

# DEFF para imprimirlo
D = deff(ICC, k)

# Estratos
estratos = (
    df_inf.groupby("macroarea")["titulo"]
    .count()
    .reset_index()
    .rename(columns={"titulo": "N_h"})
)
estratos["W_h"]    = estratos["N_h"] / N_total          # peso estrato
estratos["n_prop"] = (estratos["W_h"] * n_global).apply(ceil)  # asignación proporcional
estratos["n_final"] = estratos[["n_prop"]].apply(
    lambda x: max(x["n_prop"], STRATA_MINIMO), axis=1
)
# Ajustar si n_final > N_h (censo en estratos pequeños)
estratos["n_final"] = np.minimum(estratos["n_final"], estratos["N_h"])
estratos["n_articulos"] = estratos["n_final"] * k
estratos["pct_cobertura"] = (estratos["n_final"] / estratos["N_h"] * 100).round(1)

n_total_revistas  = estratos["n_final"].sum()
n_total_articulos = estratos["n_articulos"].sum()

# ---------------------------------------------------------------------------
# Selección aleatoria de la muestra
# ---------------------------------------------------------------------------

np.random.seed(42)
muestra_list = []

for _, row in estratos.iterrows():
    area  = row["macroarea"]
    n_sel = int(row["n_final"])
    pool  = df_inf[df_inf["macroarea"] == area]
    sel   = pool.sample(n=n_sel, random_state=42)
    sel   = sel.copy()
    sel["articulos_a_revisar"] = k
    muestra_list.append(sel)

muestra = pd.concat(muestra_list).sort_values(["macroarea", "titulo"]).reset_index(drop=True)
muestra.index += 1
muestra.index.name = "id_muestra"

# ---------------------------------------------------------------------------
# Reporte
# ---------------------------------------------------------------------------

SEP = "=" * 72

print(SEP)
print("  DISEÑO MUESTRAL — FALLAS EN INFERENCIA ESTADÍSTICA")
print("  América del Sur | Fuente: DOAJ")
print(SEP)

print(f"""
PARÁMETROS DEL DISEÑO
  Nivel de confianza          : 95%  (Z = {Z})
  Universo (N)                : {N_total:,} revistas inferenciales

  MÉTRICA M2 — % revistas con ≥1 artículo con falla (nivel revista)
    Error máximo (E)          : ±{E_M2*100:.0f} puntos porcentuales
    p esperada                : {p_M2} (conservador)
    n sin corrección          : {n0_M2:.0f}
    n con corrección FPC      : {n_M2}

  MÉTRICA M1 — % artículos con falla dentro de cada revista (nivel artículo)
    Error máximo (E)          : ±{E_M1*100:.0f} puntos porcentuales
    p esperada (artículos)    : {p_M1}
    ICC estimado              : {ICC}  →  DEFF = {D:.2f}
    Artículos por revista (k) : {k}
    Revistas necesarias       : {n_M1_fpc} (con FPC)

  TAMAÑO MUESTRAL RECTOR     : max({n_M2}, {n_M1_fpc}) = {n_global} revistas
  (se usa el mayor de los dos para satisfacer ambas métricas)
""")

print(SEP)
print(f"  ASIGNACIÓN PROPORCIONAL POR ESTRATO")
print(SEP)
print(f"  {'Macroárea':<42} {'N_h':>6} {'W_h':>6} {'n_rev':>6} {'n_art':>6} {'Cob%':>6}")
print("  " + "-" * 70)
for _, r in estratos.sort_values("N_h", ascending=False).iterrows():
    print(f"  {r['macroarea']:<42} {r['N_h']:>6} {r['W_h']:>6.3f} "
          f"{r['n_final']:>6} {r['n_articulos']:>6} {r['pct_cobertura']:>5.1f}%")
print("  " + "-" * 70)
print(f"  {'TOTAL':<42} {N_total:>6} {'1.000':>6} {n_total_revistas:>6} {n_total_articulos:>6}")

print(f"""
RESUMEN OPERATIVO
  Revistas a evaluar          : {n_total_revistas}
  Artículos a revisar (total) : {n_total_articulos}  ({k} por revista)
  Artículos por estrato       : ver tabla

PROTOCOLO DE REVISIÓN (por artículo seleccionado)
  Verificar presencia de al menos uno de estos errores:
  1. Uso de prueba paramétrica sin verificar normalidad
  2. Comparaciones múltiples sin corrección (Bonferroni, FDR, etc.)
  3. p-valor sin reporte de tamaño de efecto
  4. Confusión entre significancia estadística y práctica
  5. Muestra insuficiente / sin cálculo de potencia
  6. Variables ordinales tratadas como de razón
  7. Extrapolación fuera del ámbito del diseño muestral
""")
print(SEP)

# ---------------------------------------------------------------------------
# Guardar
# ---------------------------------------------------------------------------

cols_muestra = [
    "macroarea", "metodologia", "pais", "titulo",
    "issn_impreso", "issn_electronico",
    "editor", "idiomas", "areas_tematicas",
    "url_revista", "url_doaj",
    "proceso_revision", "tiene_apc",
    "articulos_a_revisar",
]
muestra_out = muestra[[c for c in cols_muestra if c in muestra.columns]].copy()

muestra_out.to_csv(OUTPUT_MUESTRA, encoding="utf-8-sig", sep=";")
print(f"Muestra CSV   : {OUTPUT_MUESTRA}")

try:
    with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
        muestra_out.to_excel(writer, sheet_name="Muestra_revistas", index=True)
        estratos_out = estratos.sort_values("N_h", ascending=False).copy()
        estratos_out.columns = [
            "macroarea","N_universo","peso_W","n_proporcional","n_final","n_articulos","cobertura_%"
        ]
        estratos_out.to_excel(writer, sheet_name="Diseño_estratos", index=False)

        # Hoja de instrumento de codificación por artículo
        instrumento = pd.DataFrame({
            "id_revista":    [""] * 10,
            "id_articulo":   [f"Art_{i+1}" for i in range(10)],
            "titulo_art":    [""] * 10,
            "anio":          [""] * 10,
            "falla_1_normalidad":        ["S/N"] * 10,
            "falla_2_comparaciones_mult": ["S/N"] * 10,
            "falla_3_sin_tam_efecto":    ["S/N"] * 10,
            "falla_4_sig_vs_practica":   ["S/N"] * 10,
            "falla_5_potencia":          ["S/N"] * 10,
            "falla_6_escala_ordinal":    ["S/N"] * 10,
            "falla_7_extrapolacion":     ["S/N"] * 10,
            "tiene_alguna_falla":        ["S/N"] * 10,
            "notas":                     [""] * 10,
        })
        instrumento.to_excel(writer, sheet_name="Instrumento_codificacion", index=False)

    print(f"Muestra Excel : {OUTPUT_EXCEL}")
except Exception as e:
    print(f"Excel no generado: {e}")

print(SEP)
