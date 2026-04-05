from __future__ import annotations

import argparse
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import pdfplumber
from google import genai
from pydantic import BaseModel, Field

BASE_DIR = Path(r"g:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO")
INVENTARIO_DEFAULT = BASE_DIR / "universo_analitico_inferencia.csv"
OUT_SCREENING = BASE_DIR / "screening_cuant_inferencia_gemini.csv"
OUT_LOG = BASE_DIR / "screening_cuant_inferencia_log.csv"
OUT_MERGED = BASE_DIR / "universo_analitico_inferencia_actualizado.csv"
MODELO_DEFAULT = "gemini-2.5-flash"
MAX_CHARS_PDF = 20000
GUARDAR_CADA = 10
DELAY_SEG = 0.5


class ScreeningInferencia(BaseModel):
    objetivo_general: str = Field(description="Objetivo principal del estudio en una oración.")
    frase_inferencia: str = Field(description="Cita breve que evidencie inferencia estadística. Usa 'N/A' si no hay.")
    tipo_estudio: str = Field(description="Tipo de estudio principal.")
    enfoque_metodologico: str = Field(description="Cuantitativo | Cualitativo | Mixto | No aplica")
    es_cuantitativo_con_inferencia: str = Field(description="Sí | No")
    nivel_confianza: str = Field(description="Alta | Media | Baja")
    justificacion_breve: str = Field(description="Justificación breve basada en evidencia textual.")


SYSTEM_PROMPT = """Eres un metodólogo experto en investigación científica.
Tu tarea en esta etapa NO es detectar fallas metodológicas ni juzgar el muestreo.
Solo debes decidir si el artículo es un estudio cuantitativo que aplica inferencia estadística de algún tipo.

Usa es_cuantitativo_con_inferencia = \"Sí\" si el artículo utiliza al menos alguna forma de inferencia estadística,
por ejemplo: pruebas de hipótesis, p-valores, intervalos de confianza, modelos de regresión,
ANOVA, chi-cuadrado, modelos logit/probit, correlaciones inferenciales u otros procedimientos
explícitamente usados para inferir o contrastar relaciones/efectos.

Usa es_cuantitativo_con_inferencia = \"No\" si:
- el estudio es cualitativo;
- el estudio es teórico, documental, histórico o ensayo;
- solo reporta estadística descriptiva sin inferencia;
- es experimental/laboratorial pero sin procedimientos inferenciales explícitos;
- o no hay evidencia suficiente de inferencia estadística.

No evalúes si el muestreo fue bueno o malo.
No confundas \"cuantitativo\" con \"cuantitativo con inferencia\".
Si hay duda razonable, usa la evidencia textual y marca nivel_confianza = \"Media\" o \"Baja\".
Responde solo con el JSON estructurado solicitado."""


def extraer_texto_pdf(ruta_pdf: Path, max_chars: int = MAX_CHARS_PDF) -> tuple[str, str]:
    try:
        partes = []
        with pdfplumber.open(str(ruta_pdf)) as pdf:
            for pagina in pdf.pages:
                t = pagina.extract_text()
                if t:
                    partes.append(t)
                if sum(len(x) for x in partes) >= max_chars:
                    break
        texto = "\n".join(partes)
        if not texto.strip():
            return "", "PDF sin texto extraíble"
        adv = ""
        if len(texto) > max_chars:
            texto = texto[:max_chars]
            adv = f"Truncado a {max_chars} caracteres"
        return texto, adv
    except Exception as e:
        return "", f"Error al leer PDF: {e}"


def construir_prompt(row: pd.Series, texto_pdf: str) -> str:
    titulo = str(row.get("titulo", "")).strip()
    nombre = str(row.get("nombre_archivo_pdf", "")).strip()
    return f"""Analiza este artículo y decide si aplica inferencia estadística cuantitativa.

Unidad: {row.get('unidad_id', '')}
Archivo PDF: {nombre}
Título previo: {titulo}

Preguntas guía:
1. ¿El artículo usa estadística inferencial de forma explícita?
2. ¿Solo hay descripción/frecuencias o sí hay contraste/modelado inferencial?
3. ¿El enfoque es cuantitativo, cualitativo o mixto?

--- TEXTO DEL ARTÍCULO ---
{texto_pdf}
--- FIN DEL TEXTO ---
"""


def analizar_con_gemini(cliente: genai.Client, texto_pdf: str, row: pd.Series, modelo: str) -> ScreeningInferencia:
    response = cliente.models.generate_content(
        model=modelo,
        contents=construir_prompt(row, texto_pdf),
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ScreeningInferencia,
        ),
    )
    return response.parsed


def es_error_de_cuota(msg: str) -> bool:
    m = (msg or "").lower()
    return (
        "429" in m
        or "quota" in m
        or "rate limit" in m
        or "resource_exhausted" in m
        or "exceeded your current quota" in m
    )


def cargar_api_key() -> str:
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if api_key:
        return api_key
    result = subprocess.run(
        ["powershell", "-Command", "[System.Environment]::GetEnvironmentVariable('GOOGLE_API_KEY', 'User')"],
        capture_output=True,
        text=True,
    )
    api_key = result.stdout.strip()
    if api_key:
        return api_key
    raise ValueError("No se encontró GOOGLE_API_KEY ni GEMINI_API_KEY.")


def safe_read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        str(path),
        sep=";",
        encoding="utf-8-sig",
        engine="python",
        on_bad_lines="skip",
    )


def guardar(screen_rows: list[dict], log_rows: list[dict], out_csv: Path, out_log: Path) -> None:
    if screen_rows:
        pd.DataFrame(screen_rows).to_csv(str(out_csv), sep=";", encoding="utf-8-sig", index=False)
    if log_rows:
        pd.DataFrame(log_rows).to_csv(str(out_log), sep=";", encoding="utf-8-sig", index=False)


def guardar_merge(inventario: pd.DataFrame, resultados: pd.DataFrame, out_path: Path) -> None:
    merged = inventario.copy()
    if not resultados.empty:
        res = resultados.drop_duplicates(subset=["unidad_id"]).set_index("unidad_id")
        for col_inv, col_res in [
            ("objetivo_general", "objetivo_general"),
            ("frase_inferencia", "frase_inferencia"),
            ("tipo_estudio", "tipo_estudio"),
            ("enfoque_metodologico", "enfoque_metodologico"),
            ("es_cuantitativo_con_inferencia", "es_cuantitativo_con_inferencia"),
        ]:
            if col_inv not in merged.columns:
                merged[col_inv] = ""
            mask = merged["unidad_id"].isin(res.index)
            merged.loc[mask, col_inv] = merged.loc[mask, "unidad_id"].map(res[col_res])

        if "screening_previo_origen" not in merged.columns:
            merged["screening_previo_origen"] = ""
        if "pendiente_screening_gemini" not in merged.columns:
            merged["pendiente_screening_gemini"] = "Sí"
        if "justificacion_screening" not in merged.columns:
            merged["justificacion_screening"] = ""
        if "nivel_confianza_screening" not in merged.columns:
            merged["nivel_confianza_screening"] = ""

        mask = merged["unidad_id"].isin(res.index)
        merged.loc[mask, "screening_previo_origen"] = "gemini_screening_inicial"
        merged.loc[mask, "pendiente_screening_gemini"] = "No"
        merged.loc[mask, "justificacion_screening"] = merged.loc[mask, "unidad_id"].map(res["justificacion_breve"])
        merged.loc[mask, "nivel_confianza_screening"] = merged.loc[mask, "unidad_id"].map(res["nivel_confianza"])

    merged.to_csv(str(out_path), sep=";", encoding="utf-8-sig", index=False)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventario-csv", default=str(INVENTARIO_DEFAULT))
    parser.add_argument("--salida-csv", default=str(OUT_SCREENING))
    parser.add_argument("--salida-log", default=str(OUT_LOG))
    parser.add_argument("--salida-merge", default=str(OUT_MERGED))
    parser.add_argument("--modelo", default=MODELO_DEFAULT)
    parser.add_argument("--reiniciar", action="store_true")
    parser.add_argument("--limite", type=int, default=0)
    parser.add_argument("--reintentos-429", type=int, default=1)
    parser.add_argument("--espera-429", type=int, default=60)
    parser.add_argument("--cortar-en-cuota", action="store_true")
    args = parser.parse_args()

    inventario = safe_read_csv(Path(args.inventario_csv))
    mask = (inventario["pendiente_screening_gemini"].astype(str) == "Sí") & inventario["ruta_pdf"].astype(str).str.len().gt(0)
    pendientes = inventario.loc[mask].copy()
    if args.limite > 0:
        pendientes = pendientes.head(args.limite)

    salida_csv = Path(args.salida_csv)
    salida_log = Path(args.salida_log)
    salida_merge = Path(args.salida_merge)

    ya = set()
    resultados: list[dict] = []
    logs: list[dict] = []
    if not args.reiniciar and salida_csv.exists():
        prev = safe_read_csv(salida_csv)
        resultados = prev.to_dict("records")
        ya = set(prev["unidad_id"].dropna().astype(str)) if "unidad_id" in prev.columns else set()
    if not args.reiniciar and salida_log.exists():
        prev_log = safe_read_csv(salida_log)
        logs = prev_log.to_dict("records")

    pendientes = pendientes[~pendientes["unidad_id"].astype(str).isin(ya)].copy()
    if pendientes.empty:
        guardar_merge(inventario, pd.DataFrame(resultados), salida_merge)
        print("No hay unidades pendientes para screening.")
        return

    cliente = genai.Client(api_key=cargar_api_key())

    for i, (_, row) in enumerate(pendientes.iterrows(), 1):
        unidad_id = str(row["unidad_id"])
        ruta_pdf = Path(str(row["ruta_pdf"]))
        nombre = str(row.get("nombre_archivo_pdf", ruta_pdf.name))
        texto, adv = extraer_texto_pdf(ruta_pdf)

        if not texto:
            logs.append({
                "unidad_id": unidad_id,
                "nombre_archivo_pdf": nombre,
                "estado": f"SIN_TEXTO: {adv}",
                "timestamp": datetime.now().isoformat(),
            })
            continue

        try:
            analisis = analizar_con_gemini(cliente, texto, row, args.modelo)
            resultados.append({
                "unidad_id": unidad_id,
                "nombre_archivo_pdf": nombre,
                "ruta_pdf": str(ruta_pdf),
                "objetivo_general": analisis.objetivo_general,
                "frase_inferencia": analisis.frase_inferencia,
                "tipo_estudio": analisis.tipo_estudio,
                "enfoque_metodologico": analisis.enfoque_metodologico,
                "es_cuantitativo_con_inferencia": analisis.es_cuantitativo_con_inferencia,
                "nivel_confianza": analisis.nivel_confianza,
                "justificacion_breve": analisis.justificacion_breve,
                "advertencia_pdf": adv,
            })
            logs.append({
                "unidad_id": unidad_id,
                "nombre_archivo_pdf": nombre,
                "estado": "OK",
                "es_cuantitativo_con_inferencia": analisis.es_cuantitativo_con_inferencia,
                "timestamp": datetime.now().isoformat(),
            })
            print(f"[{i}/{len(pendientes)}] {nombre} -> {analisis.es_cuantitativo_con_inferencia}")
        except Exception as e:
            msg = str(e)
            if es_error_de_cuota(msg):
                ok = False
                ultimo = msg
                for _ in range(args.reintentos_429):
                    print(f"[{i}/{len(pendientes)}] {nombre} -> cuota/rate limit, espera {args.espera_429}s")
                    time.sleep(args.espera_429)
                    try:
                        analisis = analizar_con_gemini(cliente, texto, row, args.modelo)
                        resultados.append({
                            "unidad_id": unidad_id,
                            "nombre_archivo_pdf": nombre,
                            "ruta_pdf": str(ruta_pdf),
                            "objetivo_general": analisis.objetivo_general,
                            "frase_inferencia": analisis.frase_inferencia,
                            "tipo_estudio": analisis.tipo_estudio,
                            "enfoque_metodologico": analisis.enfoque_metodologico,
                            "es_cuantitativo_con_inferencia": analisis.es_cuantitativo_con_inferencia,
                            "nivel_confianza": analisis.nivel_confianza,
                            "justificacion_breve": analisis.justificacion_breve,
                            "advertencia_pdf": adv,
                        })
                        logs.append({
                            "unidad_id": unidad_id,
                            "nombre_archivo_pdf": nombre,
                            "estado": "OK (reintento)",
                            "es_cuantitativo_con_inferencia": analisis.es_cuantitativo_con_inferencia,
                            "timestamp": datetime.now().isoformat(),
                        })
                        ok = True
                        break
                    except Exception as e2:
                        ultimo = str(e2)
                        if not es_error_de_cuota(ultimo):
                            break
                if not ok:
                    logs.append({
                        "unidad_id": unidad_id,
                        "nombre_archivo_pdf": nombre,
                        "estado": f"ERROR: {ultimo}",
                        "timestamp": datetime.now().isoformat(),
                    })
                    guardar(resultados, logs, salida_csv, salida_log)
                    guardar_merge(inventario, pd.DataFrame(resultados), salida_merge)
                    if args.cortar_en_cuota:
                        print("Corte limpio por cuota agotada.")
                        return
            else:
                logs.append({
                    "unidad_id": unidad_id,
                    "nombre_archivo_pdf": nombre,
                    "estado": f"ERROR: {msg}",
                    "timestamp": datetime.now().isoformat(),
                })

        if i % GUARDAR_CADA == 0:
            guardar(resultados, logs, salida_csv, salida_log)
            guardar_merge(inventario, pd.DataFrame(resultados), salida_merge)
        time.sleep(DELAY_SEG)

    guardar(resultados, logs, salida_csv, salida_log)
    guardar_merge(inventario, pd.DataFrame(resultados), salida_merge)
    print(f"Screening guardado en: {salida_csv}")
    print(f"Log guardado en: {salida_log}")
    print(f"Inventario actualizado en: {salida_merge}")


if __name__ == "__main__":
    main()
