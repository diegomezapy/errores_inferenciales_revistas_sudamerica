"""
fetch_articulos_muestra.py
==========================
Consulta la API pública de DOAJ para obtener los artículos de las
327 revistas seleccionadas en muestra_revistas.csv.

Por cada revista:
  - Descarga hasta 100 artículos indexados en DOAJ
  - Selecciona los 10 más recientes (priorizando 2020–2025)
  - Extrae: título, año, autores, URL fulltext, DOI, abstract

Salidas:
  - base_articulos_muestra.csv      (todos los artículos)
  - base_articulos_muestra.xlsx     (ídem + hoja de log)
  - fetch_articulos_log.csv         (una fila por revista: estado, n_disponibles, n_obtenidos)

Uso:
    python fetch_articulos_muestra.py
"""

import time
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# ── Rutas ───────────────────────────────────────────────────────────────────────
BASE_DIR   = Path("j:/Mi unidad/DECENA_FACEN/04_INVESTIGACION_REPO")
INPUT_CSV  = BASE_DIR / "muestra_revistas.csv"
OUT_CSV    = BASE_DIR / "base_articulos_muestra.csv"
OUT_XLSX   = BASE_DIR / "base_articulos_muestra.xlsx"
OUT_LOG    = BASE_DIR / "fetch_articulos_log.csv"

# ── Parámetros ──────────────────────────────────────────────────────────────────
ARTICULOS_POR_REVISTA = 10        # artículos a conservar por revista
FETCH_BATCH           = 100       # artículos a pedir en cada llamada (máx DOAJ)
ANIO_MIN              = 2018      # filtro de año mínimo (para quedarnos con los recientes)
DELAY_SEG             = 0.8       # segundos entre llamadas a la API
DOAJ_API              = "https://doaj.org/api/search/articles/{query}?pageSize={n}"

# ── Extractor de campos ─────────────────────────────────────────────────────────

def extraer_issn(row) -> str | None:
    """Devuelve el mejor ISSN disponible (eISSN preferido)."""
    for col in ("issn_electronico", "issn_impreso"):
        val = row.get(col)
        if pd.notna(val) and str(val).strip():
            return str(val).strip()
    return None


def extraer_doaj_id(url_doaj: str) -> str | None:
    """Extrae el ID de DOAJ desde la URL de tabla de contenidos."""
    if pd.isna(url_doaj):
        return None
    # https://doaj.org/toc/<ID>
    parts = str(url_doaj).rstrip("/").split("/")
    return parts[-1] if parts else None


def parsear_articulo(art: dict, meta_revista: dict) -> dict:
    bib = art.get("bibjson", {})

    # Autores
    autores = "; ".join(a.get("name", "") for a in bib.get("author", []))

    # URL fulltext
    links = bib.get("link", [])
    url_ft = next((l["url"] for l in links if l.get("type") == "fulltext"), None)
    if not url_ft and links:
        url_ft = links[0].get("url")

    # DOI
    doi = next(
        (i["id"] for i in bib.get("identifier", []) if i.get("type") == "doi"),
        None,
    )

    return {
        "id_revista":    meta_revista["id_muestra"],
        "macroarea":     meta_revista["macroarea"],
        "metodologia":   meta_revista["metodologia"],
        "pais":          meta_revista["pais"],
        "revista":       meta_revista["titulo"],
        "issn":          meta_revista["issn"],
        "titulo":        bib.get("title", ""),
        "anio":          bib.get("year", ""),
        "autores":       autores,
        "url_fulltext":  url_ft or "",
        "doi":           doi or "",
        "abstract":      bib.get("abstract", ""),
        "palabras_clave": "; ".join(bib.get("keywords", [])),
    }


# ── Consulta DOAJ ───────────────────────────────────────────────────────────────

def fetch_articulos_revista(issn: str, n: int = FETCH_BATCH) -> tuple[list, int]:
    """
    Retorna (lista_articulos, total_disponibles).
    Lanza requests.exceptions.* si hay error de red.
    """
    query = f"issn%3A{issn}"
    url   = DOAJ_API.format(query=query, n=n)
    resp  = requests.get(url, timeout=20)
    resp.raise_for_status()
    data  = resp.json()
    return data.get("results", []), data.get("total", 0)


def seleccionar_recientes(articulos: list, k: int, anio_min: int) -> list:
    """
    Filtra artículos con año >= anio_min, ordena descendente por año
    y devuelve los k primeros.  Si no hay suficientes, relaja el filtro.
    """
    def anio_int(a):
        try:
            return int(a["bibjson"].get("year", 0))
        except (ValueError, TypeError):
            return 0

    recientes = [a for a in articulos if anio_int(a) >= anio_min]
    if len(recientes) < k:
        recientes = articulos            # relaja el filtro si hay pocos

    recientes.sort(key=anio_int, reverse=True)
    return recientes[:k]


# ── Main ────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("  DESCARGA DE ARTÍCULOS — MUESTRA DE REVISTAS SUDAMERICANAS")
    print(f"  Fecha: {datetime.today().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 70)

    muestra = pd.read_csv(INPUT_CSV, sep=";", encoding="utf-8-sig")
    muestra["issn"] = muestra.apply(extraer_issn, axis=1)

    sin_issn = muestra[muestra["issn"].isna()]
    print(f"\nRevistas en muestra : {len(muestra)}")
    print(f"Con ISSN            : {muestra['issn'].notna().sum()}")
    print(f"Sin ISSN (omitidas) : {len(sin_issn)}")
    if len(sin_issn):
        print("  Revistas sin ISSN:")
        for _, r in sin_issn.iterrows():
            print(f"    - {r['titulo']}")

    muestra_valida = muestra[muestra["issn"].notna()].reset_index(drop=True)

    articulos_todos = []
    log_rows = []

    total = len(muestra_valida)
    errores = 0

    for i, row in muestra_valida.iterrows():
        issn   = row["issn"]
        titulo = row["titulo"][:55]
        meta   = row.to_dict()
        meta["issn"] = issn

        try:
            arts_raw, total_doaj = fetch_articulos_revista(issn)
            arts_sel = seleccionar_recientes(arts_raw, ARTICULOS_POR_REVISTA, ANIO_MIN)
            arts_parsed = [parsear_articulo(a, meta) for a in arts_sel]
            articulos_todos.extend(arts_parsed)

            estado = "OK" if arts_parsed else "SIN_ARTICULOS"
            log_rows.append({
                "id_muestra":      row["id_muestra"],
                "titulo":          row["titulo"],
                "issn":            issn,
                "pais":            row["pais"],
                "macroarea":       row["macroarea"],
                "total_en_doaj":   total_doaj,
                "descargados":     len(arts_raw),
                "seleccionados":   len(arts_parsed),
                "estado":          estado,
            })

            barra = "█" * int((i + 1) / total * 30)
            print(f"  [{i+1:>3}/{total}] {titulo:<55}  "
                  f"DOAJ:{total_doaj:>5}  sel:{len(arts_parsed)}  {barra}")

        except Exception as e:
            errores += 1
            log_rows.append({
                "id_muestra":    row["id_muestra"],
                "titulo":        row["titulo"],
                "issn":          issn,
                "pais":          row["pais"],
                "macroarea":     row["macroarea"],
                "total_en_doaj": 0,
                "descargados":   0,
                "seleccionados": 0,
                "estado":        f"ERROR: {e}",
            })
            print(f"  [{i+1:>3}/{total}] {titulo:<55}  ⚠ ERROR: {e}")

        time.sleep(DELAY_SEG)

    # ── Construir DataFrames ─────────────────────────────────────────────────────
    df_arts = pd.DataFrame(articulos_todos)
    df_log  = pd.DataFrame(log_rows)

    # Ordenar
    if not df_arts.empty:
        df_arts["anio"] = pd.to_numeric(df_arts["anio"], errors="coerce")
        df_arts = df_arts.sort_values(
            ["macroarea", "pais", "revista", "anio"],
            ascending=[True, True, True, False]
        ).reset_index(drop=True)
        df_arts.index += 1
        df_arts.index.name = "nro"

    # ── Guardar CSV ──────────────────────────────────────────────────────────────
    df_arts.to_csv(OUT_CSV, encoding="utf-8-sig", sep=";")
    df_log.to_csv(OUT_LOG,  encoding="utf-8-sig", sep=";", index=False)
    print(f"\nCSV artículos : {OUT_CSV}")
    print(f"CSV log       : {OUT_LOG}")

    # ── Guardar Excel ────────────────────────────────────────────────────────────
    try:
        with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
            df_arts.to_excel(writer, sheet_name="Articulos", index=True)
            df_log.to_excel(writer,  sheet_name="Log_revistas", index=False)

            # Hoja de resumen
            if not df_arts.empty:
                resumen = df_arts.groupby("macroarea").agg(
                    revistas=("revista", "nunique"),
                    articulos=("titulo", "count"),
                    con_url=("url_fulltext", lambda x: (x != "").sum()),
                    con_doi=("doi", lambda x: (x != "").sum()),
                ).reset_index()
                resumen["pct_url"] = (resumen["con_url"] / resumen["articulos"] * 100).round(1)
                resumen["pct_doi"] = (resumen["con_doi"] / resumen["articulos"] * 100).round(1)
                resumen.to_excel(writer, sheet_name="Resumen_macroarea", index=False)

        print(f"Excel         : {OUT_XLSX}")
    except Exception as e:
        print(f"Excel no generado: {e}")

    # ── Resumen final ────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  RESUMEN FINAL")
    print("=" * 70)
    print(f"  Revistas procesadas  : {len(muestra_valida)}")
    print(f"  Revistas con error   : {errores}")
    print(f"  Total artículos      : {len(df_arts)}")

    if not df_arts.empty:
        n_url = (df_arts["url_fulltext"] != "").sum()
        n_doi = (df_arts["doi"] != "").sum()
        print(f"  Con URL fulltext     : {n_url} ({n_url/len(df_arts)*100:.1f}%)")
        print(f"  Con DOI              : {n_doi} ({n_doi/len(df_arts)*100:.1f}%)")

        print("\n  Por macroárea:")
        for mac, grp in df_arts.groupby("macroarea"):
            n_u = (grp["url_fulltext"] != "").sum()
            print(f"    {mac:<42} {len(grp):>4} art.  URL:{n_u:>4}")

        print(f"\n  Rango de años: {int(df_arts['anio'].min())} – {int(df_arts['anio'].max())}")

    print("=" * 70)
    print("  Completado.")


if __name__ == "__main__":
    main()
