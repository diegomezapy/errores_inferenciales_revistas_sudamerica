"""
Expansion dirigida del universo para areas subrepresentadas.

Objetivo:
1) identificar nuevos articulos DOAJ con senales de inferencia y muestreo;
2) descargar sus PDFs en una carpeta separada;
3) incluir explicitamente la categoria "Ciencias sociales y humanidades".

Uso recomendado:
  py -3 expandir_descargar_areas_objetivo.py --quota-ing 25 --quota-edu 25 --quota-psi 25 --quota-csh 35 --quota-nat 25 --quota-agr 25
"""

from __future__ import annotations

import argparse
import re
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

# Reutiliza estrategias robustas de descarga ya probadas en el repo.
from descargar_pdfs_articulos import descargar_pdf


BASE = Path(r"g:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO")
REVISTAS_CSV = BASE / "revistas_clasificadas.csv"
MUESTRA_CSV = BASE / "muestra_revistas.csv"
BASE_ARTS_CSV = BASE / "base_articulos_muestra.csv"

OUT_REVISTAS = BASE / "expansion_revistas_objetivo.csv"
OUT_CANDIDATOS = BASE / "expansion_articulos_candidatos.csv"
OUT_LOG_FETCH = BASE / "expansion_fetch_log.csv"
OUT_LOG_DESC = BASE / "expansion_descarga_log.csv"
OUT_RESUMEN = BASE / "expansion_resumen_areas.csv"
PDF_DIR = BASE / "pdfs_articulos_expansion_areas"

DOAJ_API = "https://doaj.org/api/search/articles/{query}?pageSize={n}"
FETCH_BATCH = 120
SLEEP_API = 0.45
SLEEP_DL = 0.35


KW_INFERENCIA = [
    "regression",
    "anova",
    "manova",
    "logit",
    "probit",
    "odds ratio",
    "hazard ratio",
    "confidence interval",
    "p-value",
    "p <",
    "hypothesis",
    "inferential",
    "statistically significant",
    "correlation",
    "chi-square",
    "t-test",
    "wilcoxon",
    "kruskal",
    "bayesian",
    "multivariate",
    "model",
    "modelo",
    "regresion",
    "regresión",
    "intervalo de confianza",
    "valor p",
    "significativo",
    "inferencia",
    "analisis estadistico",
    "análisis estadístico",
]

KW_MUESTRA = [
    "sample",
    "sampling",
    "participants",
    "respondents",
    "survey",
    "cohort",
    "cross-sectional",
    "randomized",
    "random sample",
    "convenience sample",
    "n=",
    "muestra",
    "muestreo",
    "participantes",
    "encuesta",
    "cohorte",
    "transversal",
    "aleatorio",
    "no probabilistico",
    "no probabilístico",
    "tamano muestral",
    "tamaño muestral",
]

KW_SOCIALES = [
    "social sciences",
    "sociology",
    "economics",
    "political science",
    "public policy",
    "education",
    "psychology",
    "demography",
    "anthropology",
    "history",
    "philosophy",
    "law",
    "humanities",
    "ciencias sociales",
    "sociologia",
    "sociología",
    "economia",
    "economía",
    "ciencia politica",
    "ciencia política",
    "antropologia",
    "antropología",
    "historia",
    "filosofia",
    "filosofía",
    "humanidades",
    "derecho",
]


def _best_issn(row: pd.Series) -> str:
    for c in ("issn_electronico", "issn_impreso"):
        v = row.get(c, "")
        if pd.notna(v) and str(v).strip():
            return str(v).strip()
    return ""


def _clean_txt(*parts: str) -> str:
    return " ".join(str(p) for p in parts if pd.notna(p)).lower()


def _hits(text: str, keywords: list[str]) -> int:
    return sum(1 for k in keywords if k in text)


def _is_csh(row: pd.Series) -> bool:
    macro = str(row.get("macroarea", "")).strip()
    text = _clean_txt(row.get("areas_tematicas", ""), row.get("palabras_clave", ""), row.get("titulo", ""))
    if macro in {"Humanidades", "Derecho y Ciencias Juridicas"}:
        return True
    return _hits(text, KW_SOCIALES) > 0


def _categoria_objetivo(row: pd.Series) -> str:
    macro = str(row.get("macroarea", "")).strip()
    if macro == "Ingenieria y Tecnologia":
        return "Ingenieria y Tecnologia"
    if macro == "Educacion":
        return "Educacion"
    if macro == "Psicologia":
        return "Psicologia"
    if macro == "Ciencias Naturales y Exactas":
        return "Ciencias Naturales y Exactas"
    if macro == "Ciencias Agrarias y Ambientales":
        return "Ciencias Agrarias y Ambientales"
    if _is_csh(row):
        return "Ciencias sociales y humanidades"
    return ""


def _fetch_doaj_by_issn(issn: str) -> tuple[list[dict], int]:
    q = f"issn%3A{issn}"
    url = DOAJ_API.format(query=q, n=FETCH_BATCH)
    r = requests.get(url, timeout=28)
    r.raise_for_status()
    data = r.json()
    return data.get("results", []), int(data.get("total", 0))


def _parse_article(raw: dict, meta: dict) -> dict:
    b = raw.get("bibjson", {})
    links = b.get("link", [])
    url_ft = next((x.get("url", "") for x in links if x.get("type") == "fulltext"), "")
    if not url_ft and links:
        url_ft = links[0].get("url", "")
    doi = next((x.get("id", "") for x in b.get("identifier", []) if x.get("type") == "doi"), "")
    kw = b.get("keywords", []) or []
    text = _clean_txt(b.get("title", ""), b.get("abstract", ""), "; ".join(kw))
    s_inf = _hits(text, KW_INFERENCIA)
    s_mue = _hits(text, KW_MUESTRA)
    year = b.get("year", "")
    try:
        year = int(year)
    except Exception:
        year = 0
    return {
        "id_revista": meta["nro"],
        "revista": meta["titulo"],
        "pais": meta["pais"],
        "macroarea_origen": meta["macroarea"],
        "categoria_objetivo": meta["categoria_objetivo"],
        "issn": meta["issn"],
        "titulo_articulo": b.get("title", ""),
        "anio": year,
        "abstract": b.get("abstract", ""),
        "keywords": "; ".join(kw),
        "url_fulltext": url_ft or "",
        "doi": doi or "",
        "score_inferencia": s_inf,
        "score_muestreo": s_mue,
        "score_total": s_inf + s_mue,
        "pasa_filtro": (s_inf >= 1 and s_mue >= 1 and bool(url_ft)),
    }


def _safe_name(text: str) -> str:
    t = re.sub(r"[^\w\s-]", "", text or "").strip()
    t = re.sub(r"\s+", "_", t)
    return t[:38] if t else "sin_titulo"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quota-ing", type=int, default=25)
    ap.add_argument("--quota-edu", type=int, default=25)
    ap.add_argument("--quota-psi", type=int, default=25)
    ap.add_argument("--quota-csh", type=int, default=35)
    ap.add_argument("--quota-nat", type=int, default=0)
    ap.add_argument("--quota-agr", type=int, default=0)
    ap.add_argument("--max-arts-revista", type=int, default=3)
    ap.add_argument("--base-anual-csv", type=str, default="")
    ap.add_argument("--objetivo-anual", type=int, default=0, help="Si >0, prioriza anios con n < objetivo en [anio-min, anio-max]")
    ap.add_argument("--anio-min", type=int, default=2015)
    ap.add_argument("--anio-max", type=int, default=2026)
    ap.add_argument("--solo-seleccion", action="store_true")
    args = ap.parse_args()

    run_ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_revistas_run = BASE / f"expansion_revistas_objetivo_{run_ts}.csv"
    out_candidatos_run = BASE / f"expansion_articulos_candidatos_{run_ts}.csv"
    out_fetch_run = BASE / f"expansion_fetch_log_{run_ts}.csv"
    out_desc_run = BASE / f"expansion_descarga_log_{run_ts}.csv"
    out_resumen_run = BASE / f"expansion_resumen_areas_{run_ts}.csv"

    quotas = {
        "Ingenieria y Tecnologia": args.quota_ing,
        "Educacion": args.quota_edu,
        "Psicologia": args.quota_psi,
        "Ciencias sociales y humanidades": args.quota_csh,
        "Ciencias Naturales y Exactas": args.quota_nat,
        "Ciencias Agrarias y Ambientales": args.quota_agr,
    }
    remaining = dict(quotas)

    revistas = pd.read_csv(REVISTAS_CSV, sep=";", encoding="utf-8-sig")
    muestra = pd.read_csv(MUESTRA_CSV, sep=";", encoding="utf-8-sig")
    base_prev = pd.read_csv(BASE_ARTS_CSV, sep=";", encoding="utf-8-sig")

    prev_urls = set(base_prev["url_fulltext"].dropna().astype(str).str.strip())
    prev_dois = set(base_prev["doi"].dropna().astype(str).str.lower().str.strip())
    # Evita reciclar candidatos ya evaluados en corridas previas de expansion.
    if OUT_LOG_DESC.exists():
        prev_exp = pd.read_csv(OUT_LOG_DESC, sep=";", encoding="utf-8-sig")
        if "url_fulltext" in prev_exp.columns:
            prev_urls |= set(prev_exp["url_fulltext"].dropna().astype(str).str.strip())
        if "doi" in prev_exp.columns:
            prev_dois |= set(prev_exp["doi"].dropna().astype(str).str.lower().str.strip())

    revistas["issn"] = revistas.apply(_best_issn, axis=1)
    revistas["categoria_objetivo"] = revistas.apply(_categoria_objetivo, axis=1)
    revistas = revistas[revistas["categoria_objetivo"] != ""].copy()

    used_issn = set(muestra["issn_electronico"].dropna().astype(str)) | set(muestra["issn_impreso"].dropna().astype(str))
    revistas = revistas[~revistas["issn"].isin(used_issn)].copy()

    # Priorizamos revistas con metodologia cuantitativa/inferencial.
    revistas = revistas[revistas["metodologia"].isin(["Inferencia Estadística", "Experimental + Estadística", "Experimental"])].copy()
    revistas = revistas.sort_values(["categoria_objetivo", "Number of Article Records"], ascending=[True, False], na_position="last")
    revistas.to_csv(OUT_REVISTAS, sep=";", index=False, encoding="utf-8-sig")
    revistas.to_csv(out_revistas_run, sep=";", index=False, encoding="utf-8-sig")

    # Deficits por anio para priorizar seleccion temporal (opcional).
    deficit_anio: dict[int, int] = {}
    if args.objetivo_anual > 0 and args.base_anual_csv:
        try:
            base_anual = pd.read_csv(args.base_anual_csv, sep=";", encoding="utf-8-sig")
            anio_num = pd.to_numeric(base_anual.get("anio", pd.Series(dtype=str)).astype(str).str.extract(r"(\d{4})", expand=False), errors="coerce")
            base_anual = base_anual.assign(_anio=anio_num).dropna(subset=["_anio"]).copy()
            base_anual["_anio"] = base_anual["_anio"].astype(int)
            base_anual = base_anual[(base_anual["_anio"] >= args.anio_min) & (base_anual["_anio"] <= args.anio_max)]
            cnt = base_anual["_anio"].value_counts().to_dict()
            for y in range(args.anio_min, args.anio_max + 1):
                deficit_anio[y] = max(0, int(args.objetivo_anual) - int(cnt.get(y, 0)))
        except Exception as e:
            print(f"ADVERTENCIA: no se pudo cargar base anual ({e}). Se continua sin priorizacion por anio.")

    fetch_logs: list[dict] = []
    candidatos: list[dict] = []

    for _, r in revistas.iterrows():
        cat = r["categoria_objetivo"]
        if remaining.get(cat, 0) <= 0:
            continue
        issn = str(r.get("issn", "")).strip()
        if not issn:
            continue
        try:
            raw, total = _fetch_doaj_by_issn(issn)
        except Exception as e:
            fetch_logs.append(
                {
                    "nro": r["nro"],
                    "revista": r["titulo"],
                    "issn": issn,
                    "categoria_objetivo": cat,
                    "estado": f"ERROR:{e}",
                    "total_doaj": 0,
                    "candidatos_validos": 0,
                }
            )
            continue

        parsed = [_parse_article(x, r.to_dict()) for x in raw]
        dfp = pd.DataFrame(parsed)
        if dfp.empty:
            fetch_logs.append(
                {
                    "nro": r["nro"],
                    "revista": r["titulo"],
                    "issn": issn,
                    "categoria_objetivo": cat,
                    "estado": "SIN_ARTICULOS",
                    "total_doaj": total,
                    "candidatos_validos": 0,
                }
            )
            time.sleep(SLEEP_API)
            continue

        dfp = dfp[dfp["pasa_filtro"]].copy()
        if not dfp.empty:
            # Evita reprocesar URLs/DOI ya usados antes.
            dfp = dfp[~dfp["url_fulltext"].astype(str).str.strip().isin(prev_urls)]
            dfp = dfp[~dfp["doi"].astype(str).str.lower().str.strip().isin(prev_dois)]
            # Prioriza anios deficitarios cuando se habilita objetivo anual.
            if deficit_anio:
                dfp["year_priority"] = dfp["anio"].apply(lambda y: deficit_anio.get(int(y) if pd.notna(y) else -1, 0))
                dfp = dfp.sort_values(["year_priority", "score_total", "anio"], ascending=[False, False, False])
            else:
                dfp = dfp.sort_values(["score_total", "anio"], ascending=[False, False])

            take = min(args.max_arts_revista, remaining[cat], len(dfp))
            if take > 0:
                picks: list[dict] = []
                # 1) Consumir primero anios con deficit activo.
                if deficit_anio:
                    for _, rr in dfp.iterrows():
                        if len(picks) >= take:
                            break
                        yy = int(rr.get("anio", 0) or 0)
                        if deficit_anio.get(yy, 0) > 0:
                            picks.append(rr.to_dict())
                            deficit_anio[yy] -= 1
                    # 2) Completar cupo con los mejores restantes.
                    if len(picks) < take:
                        used_urls = {str(x.get("url_fulltext", "")).strip() for x in picks}
                        rest = dfp[~dfp["url_fulltext"].astype(str).str.strip().isin(used_urls)]
                        for _, rr in rest.iterrows():
                            if len(picks) >= take:
                                break
                            picks.append(rr.to_dict())
                else:
                    picks = dfp.head(take).to_dict("records")

                if picks:
                    candidatos.extend(picks)
                    remaining[cat] -= len(picks)

        fetch_logs.append(
            {
                "nro": r["nro"],
                "revista": r["titulo"],
                "issn": issn,
                "categoria_objetivo": cat,
                "estado": "OK",
                "total_doaj": total,
                "candidatos_validos": int(len(dfp)),
                "restantes_categoria": int(remaining[cat]),
                "deficit_anual_activo": int(sum(v for v in deficit_anio.values())) if deficit_anio else 0,
            }
        )

        if all(v <= 0 for v in remaining.values()):
            break
        time.sleep(SLEEP_API)

    df_fetch = pd.DataFrame(fetch_logs)
    df_cand = pd.DataFrame(candidatos).drop_duplicates(subset=["url_fulltext"], keep="first")
    if not df_fetch.empty:
        df_fetch.to_csv(OUT_LOG_FETCH, sep=";", index=False, encoding="utf-8-sig")
        df_fetch.to_csv(out_fetch_run, sep=";", index=False, encoding="utf-8-sig")
    if not df_cand.empty:
        df_cand = df_cand.sort_values(["categoria_objetivo", "score_total", "anio"], ascending=[True, False, False])
        df_cand.to_csv(OUT_CANDIDATOS, sep=";", index=False, encoding="utf-8-sig")
        df_cand.to_csv(out_candidatos_run, sep=";", index=False, encoding="utf-8-sig")

    if args.solo_seleccion or df_cand.empty:
        print("SELECCION_FINAL")
        print(df_cand.groupby("categoria_objetivo").size().to_string() if not df_cand.empty else "0")
        print(f"CSV_CANDIDATOS={OUT_CANDIDATOS}")
        print(f"CSV_FETCH_LOG={OUT_LOG_FETCH}")
        return

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    dl_rows: list[dict] = []
    counts_ok = defaultdict(int)

    for i, row in df_cand.reset_index(drop=True).iterrows():
        cat = row["categoria_objetivo"]
        url = str(row["url_fulltext"]).strip()
        fname = f"EXP_{cat[:4]}_{i+1:04d}_{int(row.get('anio', 0) or 0)}_{_safe_name(row.get('titulo_articulo',''))}.pdf"
        out = PDF_DIR / fname
        status = "ERROR"
        detalle = ""
        bytes_n = 0
        try:
            data, estrategia = descargar_pdf(url)
            if data:
                out.write_bytes(data)
                status = "OK"
                detalle = estrategia
                bytes_n = len(data)
                counts_ok[cat] += 1
            else:
                status = "SIN_PDF"
                detalle = estrategia
        except Exception as e:
            status = "ERROR"
            detalle = str(e)

        dl_rows.append(
            {
                "categoria_objetivo": cat,
                "revista": row["revista"],
                "titulo_articulo": row["titulo_articulo"],
                "anio": row["anio"],
                "url_fulltext": url,
                "doi": row["doi"],
                "score_total": row["score_total"],
                "estado": status,
                "detalle": detalle,
                "archivo_pdf": str(out) if status == "OK" else "",
                "bytes": bytes_n,
            }
        )
        time.sleep(SLEEP_DL)

    df_dl = pd.DataFrame(dl_rows)
    if not df_dl.empty:
        df_dl.to_csv(OUT_LOG_DESC, sep=";", index=False, encoding="utf-8-sig")
        df_dl.to_csv(out_desc_run, sep=";", index=False, encoding="utf-8-sig")

    resumen_rows = []
    for cat in quotas:
        cand_n = int((df_cand["categoria_objetivo"] == cat).sum()) if not df_cand.empty else 0
        ok_n = int((df_dl["categoria_objetivo"].eq(cat) & df_dl["estado"].eq("OK")).sum()) if not df_dl.empty else 0
        resumen_rows.append(
            {
                "categoria_objetivo": cat,
                "quota_objetivo": quotas[cat],
                "candidatos_filtrados": cand_n,
                "pdfs_descargados_ok": ok_n,
            }
        )
    df_res = pd.DataFrame(resumen_rows)
    df_res.to_csv(OUT_RESUMEN, sep=";", index=False, encoding="utf-8-sig")
    df_res.to_csv(out_resumen_run, sep=";", index=False, encoding="utf-8-sig")

    print("RESUMEN_FINAL")
    print(pd.DataFrame(resumen_rows).to_string(index=False))
    print(f"CANDIDATOS={OUT_CANDIDATOS}")
    print(f"DESCARGAS_LOG={OUT_LOG_DESC}")
    print(f"PDF_DIR={PDF_DIR}")
    print(f"RUN_TS={run_ts}")


if __name__ == "__main__":
    main()
