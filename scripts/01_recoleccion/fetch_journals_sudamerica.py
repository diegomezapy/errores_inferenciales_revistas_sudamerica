"""
Repositorio de Revistas Academicas - America del Sur
Fuente: DOAJ CSV publico (Directory of Open Access Journals)
Licencia de datos: CC0 (dominio publico)

Estrategia: descarga el CSV completo de DOAJ (~21 000 revistas globales)
y filtra los registros de America del Sur.
"""

import requests
import pandas as pd
import io
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

PAISES_SUDAMERICA = {
    "Argentina", "Bolivia", "Brazil", "Chile", "Colombia",
    "Ecuador", "Guyana", "Paraguay", "Peru", "Suriname",
    "Uruguay", "Venezuela",
}

# Traduccion de nombres en ingles (DOAJ) a espanol para el campo "pais"
NOMBRE_ES = {
    "Argentina":  "Argentina",
    "Bolivia":    "Bolivia",
    "Brazil":     "Brasil",
    "Chile":      "Chile",
    "Colombia":   "Colombia",
    "Ecuador":    "Ecuador",
    "Guyana":     "Guyana",
    "Paraguay":   "Paraguay",
    "Peru":       "Peru",
    "Suriname":   "Suriname",
    "Uruguay":    "Uruguay",
    "Venezuela":  "Venezuela",
}

DOAJ_CSV_URL = "https://doaj.org/csv"

OUTPUT_CSV   = "g:/Mi unidad/DECENA_FACEN/04_INVESTIGACION_REPO/revistas_sudamerica.csv"
OUTPUT_EXCEL = "g:/Mi unidad/DECENA_FACEN/04_INVESTIGACION_REPO/revistas_sudamerica.xlsx"

# ---------------------------------------------------------------------------
# Descarga
# ---------------------------------------------------------------------------

def download_doaj_csv() -> pd.DataFrame:
    print("Descargando CSV completo de DOAJ...", end="", flush=True)
    resp = requests.get(DOAJ_CSV_URL, timeout=120, allow_redirects=True)
    resp.raise_for_status()
    print(f" {len(resp.content) // 1024} KB descargados")
    df = pd.read_csv(io.BytesIO(resp.content), encoding="utf-8", low_memory=False)
    print(f"Total de revistas en DOAJ: {len(df)}")
    return df


def filter_sudamerica(df: pd.DataFrame) -> pd.DataFrame:
    col_pais = "Country of publisher"
    mask = df[col_pais].isin(PAISES_SUDAMERICA)
    sub = df[mask].copy()
    # Agregar nombre en espanol
    sub.insert(0, "Pais", sub[col_pais].map(NOMBRE_ES))
    return sub


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Traduce/simplifica los nombres de columnas al espanol."""
    mapping = {
        "Pais":                                          "pais",
        "Journal title":                                 "titulo",
        "Journal URL":                                   "url_revista",
        "Alternative title":                             "titulo_alternativo",
        "Journal ISSN (print version)":                  "issn_impreso",
        "Journal EISSN (online version)":                "issn_electronico",
        "Publisher":                                     "editor",
        "Country of publisher":                          "pais_ingles",
        "Society or institution":                        "institucion",
        "Platform, hosting or aggregation":              "plataforma",
        "Keywords":                                      "palabras_clave",
        "Languages in which the journal accepts manuscripts": "idiomas",
        "URL for the Editorial Board page":              "url_consejo_editorial",
        "Review process":                                "proceso_revision",
        "URL for the journal's aims & scope":            "url_alcance",
        "URL for the journal's instructions for authors": "url_instrucciones",
        "Average number of weeks between article submission and publication": "semanas_publicacion",
        "APC":                                           "tiene_apc",
        "APC information URL":                           "url_apc",
        "APC amount":                                    "apc_monto",
        "Currency":                                      "apc_moneda",
        "Waiver policy for developing countries etc":    "politica_exencion",
        "Has other charges":                             "otros_cargos",
        "Preservation Services":                         "preservacion",
        "Preservation Service: title lists":             "listas_preservacion",
        "Deposit policy directory":                      "politica_deposito",
        "Author holds copyright without restrictions":   "autor_retiene_copyright",
        "Copyright information URL":                     "url_copyright",
        "Author holds publishing rights without restrictions": "autor_retiene_derechos",
        "Publishing rights information URL":             "url_derechos",
        "DOAJ Seal":                                     "sello_doaj",
        "Continues":                                     "continua",
        "Continued By":                                  "continuada_por",
        "LCC Codes":                                     "codigos_lcc",
        "Subjects":                                      "areas_tematicas",
        "URL in DOAJ":                                   "url_doaj",
        "When did the journal start to publish all content using an open license?": "anio_licencia_abierta",
        "Added on Date":                                 "fecha_ingreso_doaj",
        "Tick if journals added since last update":      "nuevo_desde_ultima_actualizacion",
        "Number of Article Records in DOAJ":             "articulos_en_doaj",
        "Most Recent Article Added":                     "articulo_mas_reciente",
    }
    return df.rename(columns={k: v for k, v in mapping.items() if k in df.columns})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 65)
    print("  REPOSITORIO DE REVISTAS ACADEMICAS - AMERICA DEL SUR")
    print(f"  Fuente: DOAJ CSV  |  Fecha: {datetime.today().strftime('%Y-%m-%d')}")
    print("=" * 65)

    df_global = download_doaj_csv()
    df = filter_sudamerica(df_global)
    print(f"Revistas de America del Sur encontradas: {len(df)}")

    df = rename_columns(df)

    # Ordenar por pais y titulo
    df = df.sort_values(["pais", "titulo"]).reset_index(drop=True)
    df.index += 1
    df.index.name = "nro"

    # Agregar columna de fecha de descarga
    df["fecha_descarga"] = datetime.today().strftime("%Y-%m-%d")

    # --- CSV ---
    df.to_csv(OUTPUT_CSV, encoding="utf-8-sig", sep=";")
    print(f"\nCSV guardado  : {OUTPUT_CSV}")

    # --- Excel ---
    try:
        with pd.ExcelWriter(OUTPUT_EXCEL, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Revistas", index=True)

            resumen = (
                df.groupby("pais")
                .agg(total_revistas=("titulo", "count"))
                .sort_values("total_revistas", ascending=False)
                .reset_index()
            )
            resumen.to_excel(writer, sheet_name="Resumen_por_pais", index=False)

        print(f"Excel guardado: {OUTPUT_EXCEL}")
    except Exception as e:
        print(f"Excel no generado: {e}")

    # --- Resumen en pantalla ---
    print("\n--- RESUMEN POR PAIS ---")
    for _, row in resumen.iterrows():
        print(f"  {row['pais']:<15} {row['total_revistas']:>5} revistas")
    print(f"\n  TOTAL GENERAL    {len(df):>5} revistas")
    print("=" * 65)
    print("Completado.")


if __name__ == "__main__":
    main()
