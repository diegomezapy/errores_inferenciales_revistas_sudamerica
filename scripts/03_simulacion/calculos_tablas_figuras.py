"""
calculos_tablas_figuras.py
==========================
Replica la lógica del Rmd `calculosBASEFINAL.Rmd` en Python.
Lee el CSV de la base final analítica y exporta:
  - Tablas LaTeX (.tex)  → manuscrito/ARTICULO/tablasyfig/
  - Figuras PNG          → manuscrito/ARTICULO/tablasyfig/
  - Resumen por consola de los estimadores clave

Uso:
    python scripts/calculos_tablas_figuras.py
"""

import re
import unicodedata
import warnings
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

warnings.filterwarnings("ignore")

# ── Rutas ──────────────────────────────────────────────────────────────────────
BASE_CSV = Path(
    r"G:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO\bases_datos"
    r"\BASEFINAL320articulos_FILTRADA_cuantitativo_inferencial_v3mar2026.csv"
)
OUT_DIR = Path(
    r"G:\Mi unidad\DECENA_FACEN\03_TESIS\articulo_fallas_metodologicas"
    r"\manuscrito\ARTICULO\tablasyfig"
)
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Parámetros de diseño (igual que los params del Rmd) ────────────────────────
PARAMS = {
    "universo_total_revistas":    15450,
    "clasificadas_cuantitativas": 4170,   # J
    "revistas_sorteadas":         54,
    "articulos_listados":         485,
}

# ══════════════════════════════════════════════════════════════════════════════
# 1.  Utilidades
# ══════════════════════════════════════════════════════════════════════════════

def norm_name(s: str) -> str:
    """Normaliza un nombre de columna: sin tildes, minúsculas, guiones→_."""
    s = unicodedata.normalize("NFKD", str(s))
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = s.strip("_")
    return s


def to_bin(series: pd.Series) -> pd.Series:
    """Convierte Si/No/True/False/1/0 a entero 0/1 (NaN si irreconocible)."""
    yes = {"si", "sí", "yes", "true", "1", "s", "y"}
    no  = {"no", "false", "0", "n"}
    def conv(v):
        if pd.isna(v):
            return np.nan
        s = str(v).strip().lower().rstrip(".,;:")
        if s in yes:
            return 1
        if s in no:
            return 0
        return np.nan
    return series.map(conv)


def wilson_ci(k: int, n: int, z: float = 1.96):
    """IC de Wilson para proporción k/n."""
    if n <= 0 or np.isnan(k) or np.isnan(n):
        return (np.nan, np.nan, np.nan)
    p  = k / n
    z2 = z ** 2
    den = 1 + z2 / n
    num = p + z2 / (2 * n)
    rad = np.sqrt(p * (1 - p) / n + z2 / (4 * n ** 2))
    lo  = max(0.0, (num - z * rad) / den)
    hi  = min(1.0, (num + z * rad) / den)
    return (p, lo, hi)


def fmt_pct(x, digits=1) -> str:
    if np.isnan(x):
        return "NA"
    return f"{100*x:.{digits}f}\\,\\%".replace(".", ",")


def fmt_num(x, digits=3) -> str:
    if np.isnan(x):
        return "NA"
    return f"{x:.{digits}f}".replace(".", ",")


def escape_tex(s: str) -> str:
    """Escapa caracteres especiales LaTeX en una cadena."""
    s = str(s)
    s = s.replace("\\", "\\textbackslash{}")
    for ch in ("%", "_", "&", "#", "{", "}", "$"):
        s = s.replace(ch, f"\\{ch}")
    s = s.replace("~", "\\textasciitilde{}")
    s = s.replace("^", "\\textasciicircum{}")
    return s


def df_to_tex(df: pd.DataFrame, longtable=False) -> str:
    """Convierte un DataFrame a un bloque tabular LaTeX (booktabs, sin entorno table)."""
    cols = df.columns.tolist()
    col_fmt = "l" + "r" * (len(cols) - 1)
    lines = []
    env = "longtable" if longtable else "tabular"
    lines.append(f"\\begin{{{env}}}{{{col_fmt}}}")
    lines.append("\\toprule")
    header = " & ".join(escape_tex(c) for c in cols) + "\\\\"
    lines.append(header)
    lines.append("\\midrule")
    for _, row in df.iterrows():
        cells = " & ".join(escape_tex(str(v)) for v in row) + "\\\\"
        lines.append(cells)
    lines.append("\\bottomrule")
    lines.append(f"\\end{{{env}}}")
    return "\n".join(lines) + "\n"


def save_tex(df: pd.DataFrame, path: Path, longtable=False):
    path.write_text(df_to_tex(df, longtable=longtable), encoding="utf-8")
    print(f"  ✓  {path.name}")


# ══════════════════════════════════════════════════════════════════════════════
# 2.  Carga y detección de columnas (igual que pick() en el Rmd)
# ══════════════════════════════════════════════════════════════════════════════

print("── Cargando CSV …")
import csv as _csv
for enc in ("utf-8", "utf-8-sig", "latin-1"):
    try:
        DT0 = pd.read_csv(
            BASE_CSV, encoding=enc, sep=None, engine="python",
            on_bad_lines="skip"
        )
        print(f"   encoding detectado: {enc}")
        break
    except UnicodeDecodeError:
        continue
    except Exception:
        # Fallback: forzar separador ; o ,
        for sep in (";", ",", "\t"):
            try:
                DT0 = pd.read_csv(
                    BASE_CSV, encoding=enc, sep=sep,
                    on_bad_lines="skip"
                )
                print(f"   encoding={enc}, sep='{sep}'")
                break
            except Exception:
                continue
        break


print(f"   {len(DT0):,} filas × {len(DT0.columns)} columnas")

# Mapa nombre original → normalizado
orig   = list(DT0.columns)
normed = [norm_name(c) for c in orig]
nmap   = dict(zip(normed, orig))   # normalizado → original

def pick(pat: str):
    """Devuelve el nombre original de la primera columna que coincide con pat."""
    for n, o in zip(normed, orig):
        if re.search(pat, n, re.IGNORECASE) or re.search(pat, o, re.IGNORECASE):
            return o
    return None


col_rev_nom       = pick(r"^revista$|^nombre_revista$|^journal$")
col_si_no         = pick(r"incumple.*si[_\s]?no")
col_si_text       = pick(r"incumple.*no_?prob")
col_total_ref     = pick(r"ref_cantidad_articulos_por_rev")
col_anio          = pick(r"^anio$|^año$")
col_disc_rec      = pick(r"disciplina_recode")
col_muest_prob    = pick(r"muestreo_probabilistico")
col_muest_no_prob = pick(r"muestreo_no_probabilistico")
col_idioma        = pick(r"idioma")

print(f"   col_rev_nom    = {col_rev_nom}")
print(f"   col_si_no      = {col_si_no}")
print(f"   col_si_text    = {col_si_text}")
print(f"   col_total_ref  = {col_total_ref}")
print(f"   col_anio       = {col_anio}")
print(f"   col_disc_rec   = {col_disc_rec}")
print(f"   col_muest_prob = {col_muest_prob}")
print(f"   col_muest_np   = {col_muest_no_prob}")
print(f"   col_idioma     = {col_idioma}")

assert col_rev_nom is not None, "No se encontró columna de nombre de revista"
if col_si_no is None and col_si_text is None:
    raise ValueError("No se encontró columna de incumplimiento Si/No")

# ── Construir variables de análisis ──────────────────────────────────────────
DT = DT0.copy()

if col_si_no:
    DT["falla"] = to_bin(DT[col_si_no])
else:
    DT["falla"] = to_bin(DT[col_si_text])

# revista_id = nombre de revista limpiado (minúsculas, sin tildes, sin espacios extra)
# para que variantes tipográficas del mismo nombre colapsen en un solo grupo
def clean_revista(s):
    s = str(s).strip()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    return s

DT["revista_id"] = DT[col_rev_nom].map(clean_revista)
DT["anio"]       = pd.to_numeric(DT[col_anio], errors="coerce") if col_anio else np.nan

# ── disciplina_recode: mapeo desde texto libre por palabras clave ─────────────
col_disc_raw = pick(r"^disciplina$")
print(f"   col_disc_raw   = {col_disc_raw}")

# Reglas de mapeo (orden importa: la primera que coincide gana)
# El texto vienen como "Salud Pública, Economía, Medicina" → se normaliza y se buscan keywords
DISC_RULES = [
    ("Ciencias de la Salud", [
        "salud", "medic", "enferm", "odontol", "farmac", "nutrici",
        "fisioterapia", "epidemiol", "cardiolog", "oncolog", "psiquiatr",
        "neurolog", "pediatr", "ginecol", "cirugía", "cirugia", "anatomía",
        "anatomia", "nefrol", "endocrin", "gastroenter", "dermatol",
        "geriatr", "reumatol", "hematol", "urolog", "radiolog", "patolog",
        "biomédic", "biomedic", "immunol", "inmunol", "gerontol",
        "saúde", "trasplant", "respirator", "neonatal"
    ]),
    ("Ciencias Económicas y Administrativas", [
        "econom", "administr", "finanz", "contab", "gestión", "gestion",
        "negocio", "comercio", "emprend", "mercad", "logíst", "logist",
        "econometría", "econometria", "actuarial", "banca", "inversión",
        "inversion", "productividad", "management", "economics"
    ]),
    ("Ciencias Sociales y Humanidades", [
        "sociolog", "psicolog", "derecho", "ciencia polít", "ciencia polit",
        "política", "politica", "relacion", "comunicaci", "historia",
        "filosofía", "filosofia", "geograf", "antropolog", "lingüíst",
        "lingüist", "trabajo social", "crimino", "demografía", "demografia",
        "urbanismo", "periodismo", "cultural"
    ]),
    ("Ciencias Agrarias y Ambientales", [
        "agron", "agrícol", "agricol", "veterina", "zootecn", "pecuar",
        "forestal", "pesca", "acuicult", "horticultur", "ambient",
        "botán", "botan", "fitot", "entomol", "suelo", "cultivo",
        "recursos natural", "ecolog", "biolog vegetal"
    ]),
    ("Ingeniería y Tecnología", [
        "ingeniería", "ingenieria", "tecnolog", "informát", "informat",
        "software", "sistemás", "sistem", "electrón", "electron",
        "mecán", "mecan", "energét", "energet", "transporte", "telecomunic",
        "biotecnolog", "computaci"
    ]),
    ("Educación y Pedagogía", [
        "educaci", "pedagogí", "pedagogi", "didáct", "didact", "docen",
        "enseñ", "aprendiz", "curricul", "escuel", "universidad"
    ]),
]

def recode_disciplina(raw):
    if pd.isna(raw):
        return np.nan
    s = str(raw).lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    for categoria, keywords in DISC_RULES:
        if any(kw in s for kw in keywords):
            return categoria
    return "Otras disciplinas"

if col_disc_raw:
    DT["disciplina_recode"] = DT0[col_disc_raw].map(recode_disciplina)
    print(f"   Distribución disciplina_recode:\n{DT['disciplina_recode'].value_counts().to_string()}")
else:
    DT["disciplina_recode"] = np.nan
    print("  ⚠  No se encontró columna disciplina")

DT["M_j"]        = pd.to_numeric(DT[col_total_ref], errors="coerce") if col_total_ref else np.nan

if col_muest_prob:
    DT["muestreo_probabilistico"]    = to_bin(DT[col_muest_prob])
else:
    DT["muestreo_probabilistico"] = np.nan

if col_muest_no_prob:
    DT["muestreo_no_probabilistico"] = to_bin(DT[col_muest_no_prob])
else:
    DT["muestreo_no_probabilistico"] = np.nan

if col_idioma:
    DT["idioma"] = DT[col_idioma].astype(str)
else:
    DT["idioma"] = np.nan

# Filtrar filas con falla válida
DT = DT[DT["falla"].notna()].copy()
DT["falla"] = DT["falla"].astype(int)

n_total   = len(DT)
rev_unicas = DT["revista_id"].nunique()
print(f"\n   Base analítica: {n_total:,} artículos, {rev_unicas} revistas")

# ══════════════════════════════════════════════════════════════════════════════
# 3.  Agregación por revista y estimadores (mismo modelo que el Rmd)
# ══════════════════════════════════════════════════════════════════════════════

TAB_REV = (
    DT.groupby("revista_id")
    .agg(
        No    = ("falla", lambda x: (x == 0).sum()),
        Si    = ("falla", lambda x: (x == 1).sum()),
        Total = ("falla", "count"),
        M_j   = ("M_j",  lambda x: x.dropna().median() if x.notna().any() else np.nan),
    )
    .reset_index()
    .sort_values("revista_id")
)
TAB_REV["Prop"]  = TAB_REV["Si"] / TAB_REV["Total"]
TAB_REV["z_rev"] = (TAB_REV["Si"] > 0).astype(int)

J = PARAMS["clasificadas_cuantitativas"]
m = len(TAB_REV)

# Estimador nivel revista
P_rev   = TAB_REV["z_rev"].mean()
var_rev = (1 - m / J) * TAB_REV["z_rev"].var(ddof=1) / m
se_rev  = np.sqrt(var_rev)
ci_rev  = (max(0, P_rev - 1.96 * se_rev), min(1, P_rev + 1.96 * se_rev))

# Estimador Hájek nivel artículo
eff = TAB_REV.dropna(subset=["M_j"])
eff = eff[eff["M_j"] > 0]

if len(eff) > 0:
    bar_M   = eff["M_j"].mean()
    P_art   = (eff["M_j"] * eff["Prop"]).sum() / eff["M_j"].sum()
    resid   = eff["M_j"] * (eff["Prop"] - P_art)
    var_art = (1 - m / J) * (1 / (m * (m - 1) * bar_M ** 2)) * (resid ** 2).sum()
    se_art  = np.sqrt(var_art)
    ci_art  = (max(0, P_art - 1.96 * se_art), min(1, P_art + 1.96 * se_art))
    k_art   = int(TAB_REV["Si"].sum())
else:
    # Si no hay M_j usamos estimador simple (proporción cruda)
    P_art  = DT["falla"].mean()
    k_art  = int(DT["falla"].sum())
    _, lo, hi = wilson_ci(k_art, n_total)
    ci_art = (lo, hi)
    se_art = np.nan
    print("   ⚠  M_j no disponible — usando proporción cruda para nivel artículo")

k_rev = int(TAB_REV["z_rev"].sum())
print(f"\n── Estimadores principales ──────────────────────────────────────────")
print(f"   Revista : P̂ = {P_rev*100:.1f}%  IC95 [{ci_rev[0]*100:.1f}%, {ci_rev[1]*100:.1f}%]  k={k_rev}  m={m}")
print(f"   Artículo: P̂ = {P_art*100:.1f}%  IC95 [{ci_art[0]*100:.1f}%, {ci_art[1]*100:.1f}%]  k={k_art}  n={n_total}")

# ══════════════════════════════════════════════════════════════════════════════
# 4.  TABLAS LATEX
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n── Generando tablas .tex en {OUT_DIR} ──")

# ── tablaA_pipeline ──────────────────────────────────────────────────────────
pipeline_df = pd.DataFrame({
    "Etapa": [
        "Universo integrado (ciencias sociales)",
        "Clasificadas como cuantitativas probables (J)",
        "Sorteadas (previo a depuración)",
        "Base analítica final",
    ],
    "Revistas":  [
        PARAMS["universo_total_revistas"],
        PARAMS["clasificadas_cuantitativas"],
        PARAMS["revistas_sorteadas"],
        m,
    ],
    "Artículos": ["—", "—", PARAMS["articulos_listados"], n_total],
})
save_tex(pipeline_df, OUT_DIR / "tablaA_pipeline.tex")

# ── tablaB_resumen_niveles ────────────────────────────────────────────────────
resumen_df = pd.DataFrame({
    "Nivel": [
        "Revista (≥1 artículo con falla)",
        "Artículo (falla)",
    ],
    "P̂":      [fmt_pct(P_rev), fmt_pct(P_art)],
    "IC (95\\%)": [
        f"({fmt_pct(ci_rev[0])}, {fmt_pct(ci_rev[1])})",
        f"({fmt_pct(ci_art[0])}, {fmt_pct(ci_art[1])})",
    ],
    "k": [k_rev, k_art],
    "n": [m, n_total],
})
save_tex(resumen_df, OUT_DIR / "tablaB_resumen_niveles.tex")

# ── ANEXO_tablaC_por_revista ─────────────────────────────────────────────────
anexo_df = TAB_REV[["revista_id", "No", "Si", "Total"]].copy()
anexo_df["Prop"] = TAB_REV["Prop"].map(lambda x: fmt_num(x, 4))
fila_total = pd.DataFrame([{
    "revista_id": "Total general",
    "No":   int(TAB_REV["No"].sum()),
    "Si":   int(TAB_REV["Si"].sum()),
    "Total":int(TAB_REV["Total"].sum()),
    "Prop": fmt_num(TAB_REV["Si"].sum() / TAB_REV["Total"].sum(), 4),
}])
anexo_df = pd.concat([anexo_df, fila_total], ignore_index=True)
save_tex(anexo_df, OUT_DIR / "ANEXO_tablaC_por_revista_ANON.tex", longtable=True)

# ── tabla_disciplina ──────────────────────────────────────────────────────────
if col_disc_raw and not DT["disciplina_recode"].isna().all():
    disc_df = (
        DT[DT["disciplina_recode"].notna()]
        .groupby("disciplina_recode")
        .agg(k=("falla", "sum"), n=("falla", "count"))
        .reset_index()
    )
    disc_df["p"]   = disc_df["k"] / disc_df["n"]
    disc_df["lo"]  = disc_df.apply(lambda r: wilson_ci(r["k"], r["n"])[1], axis=1)
    disc_df["hi"]  = disc_df.apply(lambda r: wilson_ci(r["k"], r["n"])[2], axis=1)
    disc_df = disc_df.sort_values("p", ascending=False)
    disc_df["IC95"] = disc_df.apply(
        lambda r: f"({fmt_pct(r['lo'])}, {fmt_pct(r['hi'])})", axis=1)
    disc_df["p"] = disc_df["p"].map(fmt_pct)
    out_disc = disc_df[["disciplina_recode", "k", "n", "p", "IC95"]].copy()
    out_disc.columns = ["Disciplina", "k", "n", "p̂", "IC95"]
    save_tex(out_disc, OUT_DIR / "tabla_disciplina.tex")
else:
    print("  ⚠  disciplina_recode no disponible — tabla_disciplina.tex omitida")

# ── tabla_tipo_muestreo ───────────────────────────────────────────────────────
if col_muest_prob or col_muest_no_prob:
    def tipo_muestreo(row):
        if row["muestreo_probabilistico"] == 1:
            return "Probabilístico"
        if row["muestreo_no_probabilistico"] == 1:
            return "No probabilístico"
        return "No declarado"
    DT["tipo_muestreo"] = DT.apply(tipo_muestreo, axis=1)
    muest_df = (
        DT.groupby("tipo_muestreo")
        .agg(k=("falla", "sum"), n=("falla", "count"))
        .reset_index()
    )
    muest_df["p"]   = muest_df["k"] / muest_df["n"]
    muest_df["lo"]  = muest_df.apply(lambda r: wilson_ci(r["k"], r["n"])[1], axis=1)
    muest_df["hi"]  = muest_df.apply(lambda r: wilson_ci(r["k"], r["n"])[2], axis=1)
    muest_df        = muest_df.sort_values("p", ascending=False)
    muest_df["IC95"] = muest_df.apply(
        lambda r: f"({fmt_pct(r['lo'])}, {fmt_pct(r['hi'])})", axis=1)
    muest_df["p"] = muest_df["p"].map(fmt_pct)
    out_muest = muest_df[["tipo_muestreo", "k", "n", "p", "IC95"]].copy()
    out_muest.columns = ["Tipo de muestreo", "k", "n", "p̂", "IC95"]
    save_tex(out_muest, OUT_DIR / "tabla_tipo_muestreo.tex")
else:
    print("  ⚠  columnas de muestreo no disponibles — tabla_tipo_muestreo.tex omitida")

# ── tabla_resumen_sens (años ≥ 2024) ─────────────────────────────────────────
if col_anio and not DT["anio"].isna().all():
    DT_s = DT[DT["anio"] >= 2024]
    if len(DT_s) > 0:
        TAB_S = (
            DT_s.groupby("revista_id")
            .agg(
                No    = ("falla", lambda x: (x == 0).sum()),
                Si    = ("falla", "sum"),
                Total = ("falla", "count"),
                M_j   = ("M_j", lambda x: x.dropna().median() if x.notna().any() else np.nan),
            )
            .reset_index()
        )
        TAB_S["Prop"]  = TAB_S["Si"] / TAB_S["Total"]
        TAB_S["z_rev"] = (TAB_S["Si"] > 0).astype(int)
        m_s = len(TAB_S)
        P_rev_s  = TAB_S["z_rev"].mean()
        var_rs   = (1 - m_s / J) * TAB_S["z_rev"].var(ddof=1) / m_s
        se_rs    = np.sqrt(var_rs)
        ci_rs    = (max(0, P_rev_s - 1.96*se_rs), min(1, P_rev_s + 1.96*se_rs))
        eff_s    = TAB_S.dropna(subset=["M_j"])
        eff_s    = eff_s[eff_s["M_j"] > 0]
        if len(eff_s) > 1:
            bM_s  = eff_s["M_j"].mean()
            P_a_s = (eff_s["M_j"] * eff_s["Prop"]).sum() / eff_s["M_j"].sum()
            res_s = eff_s["M_j"] * (eff_s["Prop"] - P_a_s)
            var_as= (1 - m_s/J) * (1/(m_s*(m_s-1)*bM_s**2)) * (res_s**2).sum()
            se_as = np.sqrt(var_as)
            ci_as = (max(0, P_a_s - 1.96*se_as), min(1, P_a_s + 1.96*se_as))
        else:
            k_as  = int(DT_s["falla"].sum())
            P_a_s, lo_as, hi_as = wilson_ci(k_as, len(DT_s))
            ci_as = (lo_as, hi_as)
        sens_df = pd.DataFrame({
            "Nivel": ["Revista (≥1 falla, ≥2024)", "Artículo (falla, ≥2024)"],
            "P̂":    [fmt_pct(P_rev_s), fmt_pct(P_a_s)],
            "IC (95\\%)": [
                f"({fmt_pct(ci_rs[0])}, {fmt_pct(ci_rs[1])})",
                f"({fmt_pct(ci_as[0])}, {fmt_pct(ci_as[1])})",
            ],
            "k": [int(TAB_S["z_rev"].sum()), int(TAB_S["Si"].sum())],
            "n": [m_s, len(DT_s)],
        })
        save_tex(sens_df, OUT_DIR / "tabla_resumen_sens.tex")
    else:
        print("  ⚠  Sin datos ≥2024 — tabla_resumen_sens.tex omitida")
else:
    print("  ⚠  columna anio no disponible — tabla_resumen_sens.tex omitida")

# ══════════════════════════════════════════════════════════════════════════════
# 5.  FIGURAS
# ══════════════════════════════════════════════════════════════════════════════
print(f"\n── Generando figuras .png en {OUT_DIR} ──")

# ── figA: Forest plot ─────────────────────────────────────────────────────────
ci_rev_all = TAB_REV.apply(
    lambda r: wilson_ci(r["Si"], r["Total"]), axis=1, result_type="expand"
)
ci_rev_all.columns = ["Prop", "lo", "hi"]
plot_data = (
    pd.concat([TAB_REV[["revista_id"]], ci_rev_all], axis=1)
    .sort_values("Prop")
)

fig_h = max(6, 0.22 * len(plot_data))
fig, ax = plt.subplots(figsize=(8, fig_h))
ys = range(len(plot_data))
ax.errorbar(
    plot_data["Prop"], list(ys),
    xerr=[
        plot_data["Prop"] - plot_data["lo"],
        plot_data["hi"]   - plot_data["Prop"],
    ],
    fmt="o", markersize=4, color="black", ecolor="black", linewidth=0.8, capsize=2,
)
ax.set_yticks(list(ys))
ax.set_yticklabels(plot_data["revista_id"], fontsize=6)
ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
ax.set_xlabel("Proporción de artículos con falla")
ax.set_ylabel("Revista")
ax.set_title("Forest plot por revista con IC Wilson 95 %")
ax.grid(axis="x", linestyle="--", alpha=0.4)
plt.tight_layout()
plt.savefig(OUT_DIR / "figA_forest.png", dpi=300)
plt.close()
print(f"  ✓  figA_forest.png")

# ── figB: Histograma de proporciones ─────────────────────────────────────────
prop_global = TAB_REV["Si"].sum() / TAB_REV["Total"].sum()
fig, ax = plt.subplots(figsize=(8, 4))
ax.hist(TAB_REV["Prop"], bins=12, range=(0, 1), edgecolor="white", color="steelblue")
ax.axvline(prop_global, linestyle="--", color="red", linewidth=1.2,
           label=f"Media global {prop_global*100:.1f}%")
ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
ax.set_xlabel("Proporción por revista")
ax.set_ylabel("Frecuencia")
ax.set_title("Distribución de proporciones de falla por revista")
ax.legend(fontsize=9)
plt.tight_layout()
plt.savefig(OUT_DIR / "figB_hist.png", dpi=300)
plt.close()
print(f"  ✓  figB_hist.png")

# ── figC: Barras por disciplina ───────────────────────────────────────────────
if col_disc_rec and not DT["disciplina_recode"].isna().all() and "disc_df" in dir():
    disc_sorted = disc_df_raw = (
        DT[DT["disciplina_recode"] != "nan"]
        .groupby("disciplina_recode")
        .agg(k=("falla","sum"), n=("falla","count"))
        .reset_index()
    )
    disc_sorted["p"] = disc_sorted["k"] / disc_sorted["n"]
    disc_sorted = disc_sorted.sort_values("p")

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.barh(disc_sorted["disciplina_recode"], disc_sorted["p"], color="steelblue")
    ax.xaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
    ax.set_xlabel("Proporción de fallas")
    ax.set_title("Proporción de fallas por disciplina")
    plt.tight_layout()
    plt.savefig(OUT_DIR / "figC_bar_disc.png", dpi=300)
    plt.close()
    print(f"  ✓  figC_bar_disc.png")

# ══════════════════════════════════════════════════════════════════════════════
# 6.  Resumen final para actualizar resultados.tex manualmente
# ══════════════════════════════════════════════════════════════════════════════
print(f"""
══════════════════════════════════════════════════════
VALORES CLAVE PARA ACTUALIZAR resultados.tex:
──────────────────────────────────────────────────────
Artículos base analítica : {n_total}
Revistas                 : {m}

PREVALENCIA GLOBAL:
  Revista : {P_rev*100:.1f}%  IC95 [{ci_rev[0]*100:.1f}%–{ci_rev[1]*100:.1f}%]  k={k_rev}  n={m}
  Artículo: {P_art*100:.1f}%  IC95 [{ci_art[0]*100:.1f}%–{ci_art[1]*100:.1f}%]  k={k_art}  n={n_total}
══════════════════════════════════════════════════════
""")
