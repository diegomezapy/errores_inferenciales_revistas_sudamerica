"""
validacion_app.py
=================
Aplicación Streamlit para validación humana de artículos científicos.

Uso:
    streamlit run validacion_app.py

Flujo:
  1. Muestra el PDF a la derecha y el formulario a la izquierda
  2. Guarda evaluación y pasa al siguiente artículo
  3. Al terminar los 150, muestra métricas + comparación con Gemini
"""

import streamlit as st
import pandas as pd
import numpy as np
import fitz  # PyMuPDF
from pathlib import Path
from datetime import datetime

# ── Rutas ─────────────────────────────────────────────────────────────────────
VAL_DIR   = Path("j:/Mi unidad/DECENA_FACEN/04_INVESTIGACION_REPO/validacion_humana")
CSV_CIEGO = VAL_DIR / "muestra_validacion_CIEGO.csv"
CSV_COMP  = VAL_DIR / "muestra_validacion_COMPLETA.csv"
CSV_PROG  = VAL_DIR / "progreso_validacion.csv"   # guarda avance incremental

st.set_page_config(
    page_title="Validación Metodológica",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.big-metric { font-size: 2.2rem; font-weight: 700; }
.label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
.frase { background: #1e1e2e; border-left: 3px solid #7c3aed; padding: 8px 12px;
         border-radius: 4px; font-size: 0.88rem; color: #cdd6f4; margin: 4px 0; }
.badge-si  { background:#dc2626; color:white; padding:2px 10px; border-radius:12px; font-size:0.8rem; }
.badge-no  { background:#16a34a; color:white; padding:2px 10px; border-radius:12px; font-size:0.8rem; }
.badge-na  { background:#6b7280; color:white; padding:2px 10px; border-radius:12px; font-size:0.8rem; }
div[data-testid="stHorizontalBlock"] { align-items: flex-start; }
</style>
""", unsafe_allow_html=True)


# ── Carga de datos ────────────────────────────────────────────────────────────
@st.cache_data
def cargar_datos():
    ciego = pd.read_csv(CSV_CIEGO, sep=";", encoding="utf-8-sig", index_col="nro_validacion")
    comp  = pd.read_csv(CSV_COMP,  sep=";", encoding="utf-8-sig", index_col="nro_validacion")
    return ciego, comp

ciego, comp = cargar_datos()

# ── Cargar progreso guardado ──────────────────────────────────────────────────
def cargar_progreso():
    if CSV_PROG.exists():
        df = pd.read_csv(CSV_PROG, sep=";", encoding="utf-8-sig")
        # Limpiar columna índice duplicada si existe
        if "Unnamed: 0" in df.columns:
            df = df.drop(columns=["Unnamed: 0"])
        if "nro_validacion" in df.columns:
            df = df.set_index("nro_validacion")
        return df
    return pd.DataFrame(columns=["validacion_humana","comentario","timestamp"])

def guardar_progreso(prog_df):
    prog_df.index.name = "nro_validacion"
    prog_df.to_csv(CSV_PROG, sep=";", encoding="utf-8-sig")

# ── Estado de sesión ──────────────────────────────────────────────────────────
if "progreso" not in st.session_state:
    st.session_state.progreso = cargar_progreso()

if "idx" not in st.session_state:
    # Empezar en el primer artículo no evaluado
    ya_eval = set(st.session_state.progreso.index.tolist())
    pendientes = [i for i in ciego.index if i not in ya_eval]
    st.session_state.idx = pendientes[0] if pendientes else -1

prog = st.session_state.progreso
total = len(ciego)
n_eval = len(prog)
pendientes_idx = [i for i in ciego.index if i not in prog.index]


# ── Render PDF como imágenes ──────────────────────────────────────────────────
@st.cache_data
def pdf_a_imagenes(pdf_path: str, max_pags: int = 15):
    doc = fitz.open(pdf_path)
    imagenes = []
    for i, pag in enumerate(doc):
        if i >= max_pags:
            break
        mat = fitz.Matrix(1.8, 1.8)
        pix = pag.get_pixmap(matrix=mat)
        imagenes.append(pix.tobytes("png"))
    doc.close()
    return imagenes


# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA PRINCIPAL — Evaluación
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.idx != -1 and len(pendientes_idx) > 0:

    idx = st.session_state.idx
    row_ciego = ciego.loc[idx]
    row_comp  = comp.loc[idx]

    # ── Barra de progreso ──
    st.markdown(f"### Validación humana — artículo **{n_eval + 1} / {total}**")
    st.progress(n_eval / total)
    st.markdown("---")

    col_form, col_pdf = st.columns([1, 1.6], gap="large")

    # ── COLUMNA IZQUIERDA: Formulario ────────────────────────────────────────
    with col_form:
        st.markdown(f"**{row_ciego.get('revista', '')}** &nbsp;·&nbsp; {row_ciego.get('pais', '')} &nbsp;·&nbsp; {int(row_ciego.get('anio', 0)) if str(row_ciego.get('anio','')).isdigit() else row_ciego.get('anio','')}", unsafe_allow_html=True)
        st.markdown(f"#### {row_ciego.get('titulo', '')}")

        st.markdown(f"<span class='label'>Macroárea</span><br>{row_ciego.get('macroarea','')}", unsafe_allow_html=True)
        st.markdown(f"<span class='label'>Tipo de estudio</span><br>{row_ciego.get('tipo_estudio','')}", unsafe_allow_html=True)
        st.markdown(f"<span class='label'>Diseño</span><br>{row_ciego.get('diseno_estudio','')}", unsafe_allow_html=True)
        st.markdown(f"<span class='label'>n muestral</span><br>{row_ciego.get('tamano_muestra','')}", unsafe_allow_html=True)

        st.markdown("**Fragmento inferencia:**")
        st.markdown(f"<div class='frase'>{row_ciego.get('frase_inferencia','N/A')}</div>", unsafe_allow_html=True)

        st.markdown("**Fragmento muestreo:**")
        st.markdown(f"<div class='frase'>{row_ciego.get('frase_muestreo','N/A')}</div>", unsafe_allow_html=True)

        if row_ciego.get('doi','') and str(row_ciego.get('doi','')) != 'nan':
            st.markdown(f"[🔗 Ver artículo online](https://doi.org/{row_ciego['doi']})")

        st.markdown("---")
        st.markdown("### ¿Incumple la inferencia metodológica?")
        st.caption("Criterio: usa estadística inferencial O extrapola resultados + muestra NO probabilística + NO advierte esta limitación")

        respuesta = st.radio(
            "Tu evaluación:",
            ["Sí — incumple", "No — metodología correcta", "No aplica — no usa inferencia"],
            key=f"resp_{idx}",
            horizontal=False,
        )
        comentario = st.text_area("Comentario (opcional):", key=f"com_{idx}", height=80)

        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("💾 Guardar y continuar →", type="primary", use_container_width=True):
                val = respuesta.split(" — ")[0]  # "Sí", "No", "No aplica"
                nueva_fila = pd.DataFrame(
                    [{"validacion_humana": val, "comentario": comentario,
                      "timestamp": datetime.now().isoformat()}],
                    index=pd.Index([idx], name="nro_validacion")
                )
                prog = pd.concat([prog, nueva_fila])
                st.session_state.progreso = prog
                guardar_progreso(prog)

                # Avanzar al siguiente
                restantes = [i for i in ciego.index if i not in prog.index]
                st.session_state.idx = restantes[0] if restantes else -1
                st.rerun()

        with col_b2:
            if st.button("⏭ Saltar", use_container_width=True):
                restantes = [i for i in ciego.index if i not in prog.index]
                if restantes:
                    # Rotar — poner el actual al final
                    restantes_sin = [r for r in restantes if r != idx]
                    st.session_state.idx = restantes_sin[0] if restantes_sin else restantes[0]
                    st.rerun()

    # ── COLUMNA DERECHA: PDF ─────────────────────────────────────────────────
    with col_pdf:
        pdf_path = VAL_DIR / str(row_ciego.get("nombre_archivo", ""))
        if pdf_path.exists():
            imagenes = pdf_a_imagenes(str(pdf_path))
            st.markdown(f"**{pdf_path.name}** — {len(imagenes)} páginas (mostrando máx. 15)")
            for img_bytes in imagenes:
                st.image(img_bytes, use_container_width=True)
        else:
            st.warning(f"PDF no encontrado: {pdf_path.name}")
            st.markdown(f"[Abrir URL]({row_ciego.get('url_fulltext','')})")


# ══════════════════════════════════════════════════════════════════════════════
# PANTALLA FINAL — Métricas y comparación con Gemini
# ══════════════════════════════════════════════════════════════════════════════
else:
    st.title("✅ Validación completada")
    st.markdown(f"**{n_eval} artículos evaluados** — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    st.markdown("---")

    # Unir evaluación humana con respuesta Gemini
    merged = comp.join(prog[["validacion_humana","comentario"]], how="inner", rsuffix="_humana")
    gemini_col = "incumple_inferencia"

    # Normalizar valores
    def norm(s):
        s = str(s).strip()
        if s.startswith("Sí") or s == "Si": return "Sí"
        if s.startswith("No aplica"):        return "No aplica"
        if s.startswith("No"):               return "No"
        return s

    merged["gemini"] = merged[gemini_col].apply(norm)
    merged["humano"] = merged["validacion_humana"].apply(norm)
    m = merged[merged["humano"].isin(["Sí","No"])]  # excluir No aplica

    # ── Métricas ───────────────────────────────────────────────────────────────
    from sklearn.metrics import cohen_kappa_score, confusion_matrix, classification_report

    try:
        kappa = cohen_kappa_score(m["gemini"], m["humano"])
    except Exception:
        kappa = float("nan")

    concordancia = (m["gemini"] == m["humano"]).mean()
    vp = ((m["gemini"]=="Sí") & (m["humano"]=="Sí")).sum()
    vn = ((m["gemini"]=="No") & (m["humano"]=="No")).sum()
    fp = ((m["gemini"]=="Sí") & (m["humano"]=="No")).sum()
    fn = ((m["gemini"]=="No") & (m["humano"]=="Sí")).sum()
    sens = vp/(vp+fn) if (vp+fn)>0 else 0
    espec = vn/(vn+fp) if (vn+fp)>0 else 0
    ppv  = vp/(vp+fp) if (vp+fp)>0 else 0
    npv  = vn/(vn+fn) if (vn+fn)>0 else 0

    # ── Dashboard ──────────────────────────────────────────────────────────────
    st.markdown("## Concordancia Gemini vs. Humano")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Concordancia global", f"{concordancia*100:.1f}%")
    c2.metric("Kappa de Cohen (κ)", f"{kappa:.3f}",
              help="<0.4 pobre | 0.4-0.6 moderado | 0.6-0.8 sustancial | >0.8 casi perfecto")
    c3.metric("Sensibilidad Gemini", f"{sens*100:.1f}%", help="% fallas reales que Gemini detectó")
    c4.metric("Especificidad Gemini", f"{espec*100:.1f}%", help="% correctos que Gemini clasificó bien")

    c5,c6,c7,c8 = st.columns(4)
    c5.metric("VP (falla correcta)", int(vp))
    c6.metric("VN (correcto ok)", int(vn))
    c7.metric("FP (falso positivo)", int(fp))
    c8.metric("FN (falso negativo)", int(fn))

    st.markdown("---")

    # ── Prevalencia corregida ──────────────────────────────────────────────────
    st.markdown("## Prevalencia corregida por validación")

    # Prevalencia bruta Gemini
    N_total = 563  # artículos con inferencia en base completa
    p_gemini = 449 / N_total

    # Corrección por sensibilidad/especificidad (Rogan-Gladen)
    if (sens + espec) != 1:
        p_corregida = (p_gemini + espec - 1) / (sens + espec - 1)
        p_corregida = max(0, min(1, p_corregida))
    else:
        p_corregida = p_gemini

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Prevalencia bruta (Gemini)", f"{p_gemini*100:.1f}%")
        st.metric("Prevalencia corregida (Rogan-Gladen)", f"{p_corregida*100:.1f}%")
    with col_b:
        sesgo = (p_corregida - p_gemini)*100
        st.metric("Sesgo de Gemini", f"{sesgo:+.1f} pp",
                  delta_color="inverse" if sesgo > 0 else "normal")
        st.caption("Positivo = Gemini sobreestima la falla | Negativo = subestima")

    st.markdown("---")

    # ── Tabla de discordancias ─────────────────────────────────────────────────
    st.markdown("## Artículos en discordancia")
    discord = merged[merged["gemini"] != merged["humano"]][
        ["titulo","revista","pais","gemini","humano","comentario","conclusion_falla"]
    ].rename(columns={"gemini":"Gemini","humano":"Tú","conclusion_falla":"Razonamiento Gemini"})
    st.dataframe(discord, use_container_width=True, height=400)

    st.markdown("---")

    # ── Distribución por evaluador ─────────────────────────────────────────────
    col_ev1, col_ev2 = st.columns(2)
    with col_ev1:
        st.markdown("**Tu evaluación**")
        st.dataframe(merged["humano"].value_counts().rename("n").reset_index(), use_container_width=True)
    with col_ev2:
        st.markdown("**Evaluación Gemini (misma muestra)**")
        st.dataframe(merged["gemini"].value_counts().rename("n").reset_index(), use_container_width=True)

    # ── Exportar resultados ────────────────────────────────────────────────────
    st.markdown("---")
    csv_out = merged.to_csv(sep=";", encoding="utf-8-sig").encode("utf-8-sig")
    st.download_button(
        "⬇️ Descargar resultados completos (CSV)",
        data=csv_out,
        file_name=f"validacion_comparada_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )

    # Opción de reiniciar
    st.markdown("---")
    if st.button("🔄 Reiniciar validación desde cero"):
        if CSV_PROG.exists():
            CSV_PROG.unlink()
        st.session_state.progreso = pd.DataFrame(columns=["nro_validacion","validacion_humana","comentario","timestamp"])
        st.session_state.idx = ciego.index[0]
        st.rerun()
