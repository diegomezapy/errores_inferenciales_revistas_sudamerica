from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

BASE_DIR = Path(r"g:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO")
DIR_PRINCIPAL = BASE_DIR / "pdfs_articulos"
DIR_EXTRA = BASE_DIR / "PDFs"
BASE_ARTICULOS = BASE_DIR / "base_articulos_muestra.csv"
BASE_AUDITORIA = BASE_DIR / "base_auditoria_FINAL.csv"
OUT_PDFS = BASE_DIR / "inventario_pdfs_fuentes.csv"
OUT_UNIDADES = BASE_DIR / "universo_analitico_inferencia.csv"
OUT_RESUMEN = BASE_DIR / "resumen_integracion_pdfs.json"


def read_csv_flexible(path: Path, sep: str = ";") -> pd.DataFrame:
    encodings = ["utf-8-sig", "utf-8", "latin1", "cp1252"]
    last_error: Exception | None = None
    for enc in encodings:
        try:
            return pd.read_csv(path, sep=sep, encoding=enc)
        except Exception as e:
            last_error = e
    if sep == ",":
        for enc in encodings:
            try:
                return pd.read_csv(path, sep=sep, encoding=enc, engine="python", on_bad_lines="skip")
            except Exception as e:
                last_error = e
    raise RuntimeError(f"No se pudo leer {path}: {last_error}")


def normalize_yes_no(value: Any) -> str:
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    t = text.lower()
    if t in {"si", "sí", "yes", "true", "1"}:
        return "Sí"
    if t in {"no", "false", "0"}:
        return "No"
    return text


def cargar_base_articulos() -> pd.DataFrame:
    df = read_csv_flexible(BASE_ARTICULOS)
    if "nro" not in df.columns:
        raise ValueError("base_articulos_muestra.csv no tiene columna nro")
    return df


def extraer_nro_desde_nombre(nombre_archivo: str) -> int | None:
    m = re.match(r"^(\d+)_", str(nombre_archivo).strip())
    return int(m.group(1)) if m else None


def cargar_base_auditoria() -> pd.DataFrame:
    df = read_csv_flexible(BASE_AUDITORIA)
    if "nombre_archivo" not in df.columns:
        raise ValueError("base_auditoria_FINAL.csv no tiene columna nombre_archivo")
    return df


def cargar_txt_legacy() -> pd.DataFrame:
    txt_files = sorted(DIR_EXTRA.rglob("*.txt"))
    frames: list[pd.DataFrame] = []
    for path in txt_files:
        df = read_csv_flexible(path, sep=",")
        df["source_txt"] = path.relative_to(BASE_DIR).as_posix()
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    legacy = pd.concat(frames, ignore_index=True)
    legacy.columns = [str(c).strip() for c in legacy.columns]
    return legacy


def build_pdf_inventory(base_art: pd.DataFrame, audit: pd.DataFrame) -> pd.DataFrame:
    audit_map = audit.drop_duplicates(subset=["nombre_archivo"]).set_index("nombre_archivo")
    base_map = base_art.drop_duplicates(subset=["nro"]).set_index("nro")

    rows: list[dict[str, Any]] = []

    for path in sorted(DIR_PRINCIPAL.glob("*.pdf")):
        name = path.name
        nro_pdf = extraer_nro_desde_nombre(name)
        meta = base_map.loc[nro_pdf].to_dict() if nro_pdf in base_map.index else {}
        aud = audit_map.loc[name].to_dict() if name in audit_map.index else {}
        rows.append(
            {
                "pdf_id": f"principal::{name}",
                "fuente_pdf": "pdfs_articulos",
                "subcarpeta_fuente": "pdfs_articulos",
                "nombre_archivo_pdf": name,
                "ruta_pdf": str(path),
                "ruta_relativa": path.relative_to(BASE_DIR).as_posix(),
                "es_lote_pdf": "No",
                "tiene_metadata_base": "Sí" if meta else "No",
                "tiene_screening_previo": "Sí" if aud else "No",
                "screening_previo_origen": "base_auditoria_FINAL" if aud else "",
                "titulo": meta.get("titulo", ""),
                "revista": meta.get("revista", ""),
                "pais": meta.get("pais", ""),
                "macroarea": meta.get("macroarea", ""),
                "anio": meta.get("anio", ""),
                "es_cuantitativo_con_inferencia_previo": normalize_yes_no(aud.get("es_cuantitativo_con_inferencia", "")),
                "enfoque_metodologico_previo": aud.get("enfoque_metodologico", ""),
                "tipo_estudio_previo": aud.get("tipo_estudio", ""),
            }
        )

    for path in sorted(DIR_EXTRA.rglob("*.pdf")):
        rel = path.relative_to(BASE_DIR).as_posix()
        name = path.name
        rows.append(
            {
                "pdf_id": f"extra::{rel}",
                "fuente_pdf": "PDFs",
                "subcarpeta_fuente": path.parent.relative_to(DIR_EXTRA).as_posix(),
                "nombre_archivo_pdf": name,
                "ruta_pdf": str(path),
                "ruta_relativa": rel,
                "es_lote_pdf": "Sí" if name.lower().startswith("lote_") else "No",
                "tiene_metadata_base": "No",
                "tiene_screening_previo": "No",
                "screening_previo_origen": "",
                "titulo": "",
                "revista": "",
                "pais": "",
                "macroarea": "",
                "anio": "",
                "es_cuantitativo_con_inferencia_previo": "",
                "enfoque_metodologico_previo": "",
                "tipo_estudio_previo": "",
            }
        )

    return pd.DataFrame(rows)


def build_units_inventory(base_art: pd.DataFrame, audit: pd.DataFrame, legacy: pd.DataFrame) -> pd.DataFrame:
    base_map = base_art.drop_duplicates(subset=["nro"]).set_index("nro")
    audit_map = audit.drop_duplicates(subset=["nombre_archivo"]).set_index("nombre_archivo")
    extra_pdf_by_name = {p.name: p for p in sorted(DIR_EXTRA.rglob("*.pdf"))}

    rows: list[dict[str, Any]] = []

    for path in sorted(DIR_PRINCIPAL.glob("*.pdf")):
        name = path.name
        nro_pdf = extraer_nro_desde_nombre(name)
        meta = base_map.loc[nro_pdf].to_dict() if nro_pdf in base_map.index else {}
        aud = audit_map.loc[name].to_dict() if name in audit_map.index else {}
        rows.append(
            {
                "unidad_id": f"articulo_principal::{name}",
                "unidad_tipo": "articulo_pdf_individual",
                "fuente_unidad": "pdfs_articulos",
                "nombre_archivo_pdf": name,
                "ruta_pdf": str(path),
                "ruta_relativa": path.relative_to(BASE_DIR).as_posix(),
                "titulo": meta.get("titulo", ""),
                "revista": meta.get("revista", ""),
                "pais": meta.get("pais", ""),
                "macroarea": meta.get("macroarea", ""),
                "anio": meta.get("anio", ""),
                "screening_previo_origen": "base_auditoria_FINAL" if aud else "",
                "es_cuantitativo_con_inferencia": normalize_yes_no(aud.get("es_cuantitativo_con_inferencia", "")),
                "enfoque_metodologico": aud.get("enfoque_metodologico", ""),
                "tipo_estudio": aud.get("tipo_estudio", ""),
                "frase_inferencia": aud.get("frase_inferencia", ""),
                "frase_muestreo": aud.get("frase_muestreo", ""),
                "tamano_muestra": aud.get("tamano_muestra", ""),
                "pendiente_screening_gemini": "No" if aud else "Sí",
                "observaciones_integracion": "Lote principal con metadata base y screening previo reutilizable." if aud else "Lote principal sin screening previo enlazado.",
            }
        )

    legacy_pdf_names = set()
    if not legacy.empty:
        for idx, row in legacy.iterrows():
            pdf_name = str(row.get("nombre_archivo", "")).strip()
            path = extra_pdf_by_name.get(pdf_name)
            legacy_pdf_names.add(pdf_name)
            rows.append(
                {
                    "unidad_id": f"legacy::{Path(str(row.get('source_txt', 'legacy'))).stem}::{idx+1}",
                    "unidad_tipo": "articulo_en_lote_pdf",
                    "fuente_unidad": "PDFs_txt_legacy",
                    "nombre_archivo_pdf": pdf_name,
                    "ruta_pdf": str(path) if path else "",
                    "ruta_relativa": path.relative_to(BASE_DIR).as_posix() if path else "",
                    "titulo": row.get("titulo_completo", ""),
                    "revista": row.get("revista", ""),
                    "pais": row.get("pais", ""),
                    "macroarea": row.get("macroarea", ""),
                    "anio": row.get("anio", ""),
                    "screening_previo_origen": row.get("source_txt", "txt_legacy"),
                    "es_cuantitativo_con_inferencia": normalize_yes_no(row.get("es_cuantitativo_con_inferencia", "")),
                    "enfoque_metodologico": row.get("enfoque_metodologico", ""),
                    "tipo_estudio": row.get("tipo_estudio", ""),
                    "frase_inferencia": row.get("frase_relacionada_a_inferencia", ""),
                    "frase_muestreo": row.get("frase_relacionada_a_muestreo", ""),
                    "tamano_muestra": row.get("tamano_muestra", ""),
                    "pendiente_screening_gemini": "No",
                    "observaciones_integracion": "Registro artículo-a-artículo recuperado desde txt legacy asociado a un PDF por lotes.",
                }
            )

    for path in sorted(DIR_EXTRA.rglob("*.pdf")):
        name = path.name
        is_lote = name.lower().startswith("lote_")
        if is_lote:
            has_legacy = name in legacy_pdf_names
            rows.append(
                {
                    "unidad_id": f"lote_pdf::{path.relative_to(BASE_DIR).as_posix()}",
                    "unidad_tipo": "pdf_lote_multiarticulo",
                    "fuente_unidad": "PDFs",
                    "nombre_archivo_pdf": name,
                    "ruta_pdf": str(path),
                    "ruta_relativa": path.relative_to(BASE_DIR).as_posix(),
                    "titulo": "",
                    "revista": "",
                    "pais": "",
                    "macroarea": "",
                    "anio": "",
                    "screening_previo_origen": "txt_legacy" if has_legacy else "",
                    "es_cuantitativo_con_inferencia": "",
                    "enfoque_metodologico": "",
                    "tipo_estudio": "",
                    "frase_inferencia": "",
                    "frase_muestreo": "",
                    "tamano_muestra": "",
                    "pendiente_screening_gemini": "No",
                    "observaciones_integracion": "PDF por lotes; no enviar a screening directo como unidad única. Usar registros legacy si existen o desagregar antes.",
                }
            )
        else:
            rows.append(
                {
                    "unidad_id": f"extra_pdf::{path.relative_to(BASE_DIR).as_posix()}",
                    "unidad_tipo": "articulo_pdf_individual_extra",
                    "fuente_unidad": "PDFs",
                    "nombre_archivo_pdf": name,
                    "ruta_pdf": str(path),
                    "ruta_relativa": path.relative_to(BASE_DIR).as_posix(),
                    "titulo": "",
                    "revista": "",
                    "pais": "",
                    "macroarea": "",
                    "anio": "",
                    "screening_previo_origen": "",
                    "es_cuantitativo_con_inferencia": "",
                    "enfoque_metodologico": "",
                    "tipo_estudio": "",
                    "frase_inferencia": "",
                    "frase_muestreo": "",
                    "tamano_muestra": "",
                    "pendiente_screening_gemini": "Sí",
                    "observaciones_integracion": "PDF extra individual sin screening previo; candidato al primer filtro con Gemini.",
                }
            )

    df = pd.DataFrame(rows)
    df = df.drop_duplicates(subset=["unidad_id"]).sort_values(["fuente_unidad", "unidad_tipo", "nombre_archivo_pdf"]).reset_index(drop=True)
    df.index = range(1, len(df) + 1)
    df.index.name = "nro"
    return df


def main() -> None:
    base_art = cargar_base_articulos()
    audit = cargar_base_auditoria()
    legacy = cargar_txt_legacy()

    pdf_inv = build_pdf_inventory(base_art, audit)
    pdf_inv = pdf_inv.sort_values(["fuente_pdf", "subcarpeta_fuente", "nombre_archivo_pdf"]).reset_index(drop=True)
    pdf_inv.index = range(1, len(pdf_inv) + 1)
    pdf_inv.index.name = "nro"
    pdf_inv.to_csv(OUT_PDFS, sep=";", encoding="utf-8-sig")

    units = build_units_inventory(base_art, audit, legacy)
    units.to_csv(OUT_UNIDADES, sep=";", encoding="utf-8-sig")

    summary = {
        "pdfs_articulos_pdfs": int((pdf_inv["fuente_pdf"] == "pdfs_articulos").sum()),
        "pdfs_extra_pdfs": int((pdf_inv["fuente_pdf"] == "PDFs").sum()),
        "total_pdfs": int(len(pdf_inv)),
        "unidades_totales": int(len(units)),
        "unidades_con_screening_previo": int(units["es_cuantitativo_con_inferencia"].astype(str).str.len().gt(0).sum()),
        "unidades_pendientes_screening_gemini": int((units["pendiente_screening_gemini"] == "Sí").sum()),
        "pdfs_lote_multiarticulo": int((units["unidad_tipo"] == "pdf_lote_multiarticulo").sum()),
        "articulos_legacy_en_lotes": int((units["unidad_tipo"] == "articulo_en_lote_pdf").sum()),
        "articulos_extra_individuales": int((units["unidad_tipo"] == "articulo_pdf_individual_extra").sum()),
        "articulos_principales": int((units["unidad_tipo"] == "articulo_pdf_individual").sum()),
    }
    OUT_RESUMEN.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"CSV PDFs: {OUT_PDFS}")
    print(f"CSV unidades: {OUT_UNIDADES}")
    print(f"Resumen: {OUT_RESUMEN}")


if __name__ == "__main__":
    main()


