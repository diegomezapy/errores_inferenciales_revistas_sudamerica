from __future__ import annotations

import argparse
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from google import genai
from pydantic import BaseModel, Field


BASE_DIR = Path(r"g:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO")
IN_CSV = BASE_DIR / "lista_final_universo_si_cuant_inferencia.csv"
OUT_CSV = BASE_DIR / "macroarea_deducida_211_gemini.csv"
OUT_LOG = BASE_DIR / "macroarea_deducida_211_gemini_log.csv"
OUT_FINAL = BASE_DIR / "lista_final_universo_si_cuant_inferencia_con_macroarea.csv"
OUT_TABLE = BASE_DIR / "tabla_por_area_universo_si_con_macroarea_deducida.csv"
OUT_REPORT = BASE_DIR / "REPORTE_DEDUCCION_MACROAREA_211_2026-04-01.md"
MODELO_DEFAULT = "gemini-2.5-flash"
GUARDAR_CADA = 10
DELAY_SEG = 0.5

AREAS = [
    "Ciencias Agrarias y Ambientales",
    "Ciencias Naturales y Exactas",
    "Ciencias de la Salud",
    "Educación",
    "Ingeniería y Tecnología",
    "Psicología",
]


class ClasificacionMacroarea(BaseModel):
    macroarea_deducida: str = Field(
        description="Una de estas categorías: Ciencias Agrarias y Ambientales | Ciencias Naturales y Exactas | Ciencias de la Salud | Educación | Ingeniería y Tecnología | Psicología"
    )
    nivel_confianza_macroarea: str = Field(description="Alta | Media | Baja")
    justificacion_macroarea: str = Field(description="Justificación breve basada en título, objetivo, revista y dominio temático.")


SYSTEM_PROMPT = """Eres un metodólogo y clasificador temático.
Tu tarea NO es decidir si el estudio es bueno o malo, ni si tiene fallas.
Solo debes deducir la macroárea temática más plausible de cada artículo.

Debes elegir exactamente una categoría de esta lista:
- Ciencias Agrarias y Ambientales
- Ciencias Naturales y Exactas
- Ciencias de la Salud
- Educación
- Ingeniería y Tecnología
- Psicología

Reglas:
- Prioriza el dominio sustantivo del artículo, no la técnica estadística.
- Si el artículo es de psiquiatría, neuropsicología, salud mental clínica o intervención en pacientes, normalmente corresponde primero a Ciencias de la Salud, salvo que el foco principal sea psicológico/psicométrico/conductual no clínico.
- Usa Psicología para estudios centrados en procesos psicológicos, psicometría, emoción, conducta, cognición, personalidad, o fenómenos psicológicos.
- Usa Educación para aprendizaje, escuelas, evaluación educativa, formación docente, currículo y desempeño escolar.
- Usa Ingeniería y Tecnología para sistemas, algoritmos, procesos industriales, infraestructura, diseño técnico, manufactura, materiales aplicados o tecnología.
- Usa Ciencias Agrarias y Ambientales para agricultura, veterinaria, agronomía, alimentos, recursos naturales, ecosistemas, ambiente, suelos, cultivos y producción animal.
- Usa Ciencias Naturales y Exactas para física, química, matemática, biología básica, ciencias de materiales no claramente aplicadas, y ciencias naturales sin foco clínico o agrario.
- Usa Ciencias de la Salud para medicina, enfermería, salud pública, epidemiología clínica, psiquiatría clínica, rehabilitación, nutrición clínica y otras ciencias biomédicas aplicadas a personas/pacientes.

Si hay duda entre dos áreas, elige la más defendible y marca confianza Media o Baja.
Responde solo con el JSON solicitado."""


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
    return pd.read_csv(str(path), sep=";", encoding="utf-8-sig", engine="python", on_bad_lines="skip")


def es_error_de_cuota(msg: str) -> bool:
    m = (msg or "").lower()
    return (
        "429" in m
        or "quota" in m
        or "rate limit" in m
        or "resource_exhausted" in m
        or "exceeded your current quota" in m
    )


def construir_prompt(row: pd.Series) -> str:
    campos = {
        "unidad_id": row.get("unidad_id", ""),
        "archivo": row.get("nombre_archivo_pdf", ""),
        "titulo": row.get("titulo", ""),
        "revista": row.get("revista", ""),
        "pais": row.get("pais", ""),
        "objetivo_general": row.get("objetivo_general", ""),
        "frase_inferencia": row.get("frase_inferencia", ""),
        "tipo_estudio": row.get("tipo_estudio", ""),
        "enfoque_metodologico": row.get("enfoque_metodologico", ""),
        "justificacion_screening": row.get("justificacion_screening", ""),
    }
    return "\n".join([f"{k}: {v}" for k, v in campos.items()])


def analizar_con_gemini(cliente: genai.Client, row: pd.Series, modelo: str) -> ClasificacionMacroarea:
    response = cliente.models.generate_content(
        model=modelo,
        contents=construir_prompt(row),
        config=genai.types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=ClasificacionMacroarea,
        ),
    )
    return response.parsed


def guardar(rows: list[dict], logs: list[dict], out_csv: Path, out_log: Path) -> None:
    if rows:
        pd.DataFrame(rows).to_csv(str(out_csv), sep=";", encoding="utf-8-sig", index=False)
    if logs:
        pd.DataFrame(logs).to_csv(str(out_log), sep=";", encoding="utf-8-sig", index=False)


def construir_salida_final(df_base: pd.DataFrame, df_res: pd.DataFrame) -> pd.DataFrame:
    out = df_base.copy()
    res = df_res.drop_duplicates(subset=["unidad_id"], keep="last").set_index("unidad_id")
    mask = out["unidad_id"].astype(str).isin(res.index)

    if "macroarea_deducida" not in out.columns:
        out["macroarea_deducida"] = ""
    if "nivel_confianza_macroarea" not in out.columns:
        out["nivel_confianza_macroarea"] = ""
    if "justificacion_macroarea" not in out.columns:
        out["justificacion_macroarea"] = ""

    out.loc[mask, "macroarea_deducida"] = out.loc[mask, "unidad_id"].map(res["macroarea_deducida"])
    out.loc[mask, "nivel_confianza_macroarea"] = out.loc[mask, "unidad_id"].map(res["nivel_confianza_macroarea"])
    out.loc[mask, "justificacion_macroarea"] = out.loc[mask, "unidad_id"].map(res["justificacion_macroarea"])

    out["macroarea_final"] = out["macroarea"]
    mask_missing = out["macroarea_final"].isna() | out["macroarea_final"].astype(str).str.strip().eq("")
    out.loc[mask_missing, "macroarea_final"] = out.loc[mask_missing, "macroarea_deducida"]
    return out


def guardar_tabla_y_reporte(df_final: pd.DataFrame) -> None:
    tabla = (
        df_final.assign(macroarea_final=df_final["macroarea_final"].fillna("SIN_MACROAREA"))
        .groupby("macroarea_final")
        .size()
        .reset_index(name="n")
        .sort_values(["n", "macroarea_final"], ascending=[False, True])
    )
    tabla["pct_total"] = (tabla["n"] / len(df_final) * 100).round(1)
    tabla.to_csv(str(OUT_TABLE), sep=";", encoding="utf-8-sig", index=False)

    ded = df_final["macroarea_deducida"].astype(str).str.strip().ne("").sum()
    alta = df_final["nivel_confianza_macroarea"].astype(str).eq("Alta").sum()
    media = df_final["nivel_confianza_macroarea"].astype(str).eq("Media").sum()
    baja = df_final["nivel_confianza_macroarea"].astype(str).eq("Baja").sum()

    lines = [
        "# Reporte de deducción de macroárea para los 211 casos faltantes",
        "",
        "Fecha: `2026-04-01`",
        "",
        "## Resultado general",
        "",
        f"- Casos sin `macroarea` original revisados: `211`",
        f"- Casos con `macroarea_deducida` asignada: `{ded}`",
        f"- Confianza `Alta`: `{alta}`",
        f"- Confianza `Media`: `{media}`",
        f"- Confianza `Baja`: `{baja}`",
        "",
        "## Tabla final por área",
        "",
        "| Área | n | % |",
        "|---|---:|---:|",
    ]
    for _, row in tabla.iterrows():
        lines.append(f"| {row['macroarea_final']} | {int(row['n'])} | {row['pct_total']:.1f} |")
    OUT_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-csv", default=str(IN_CSV))
    parser.add_argument("--output-csv", default=str(OUT_CSV))
    parser.add_argument("--output-log", default=str(OUT_LOG))
    parser.add_argument("--output-final", default=str(OUT_FINAL))
    parser.add_argument("--modelo", default=MODELO_DEFAULT)
    parser.add_argument("--reiniciar", action="store_true")
    parser.add_argument("--limite", type=int, default=0)
    parser.add_argument("--reintentos-429", type=int, default=1)
    parser.add_argument("--espera-429", type=int, default=60)
    parser.add_argument("--cortar-en-cuota", action="store_true")
    args = parser.parse_args()

    input_csv = Path(args.input_csv)
    output_csv = Path(args.output_csv)
    output_log = Path(args.output_log)
    output_final = Path(args.output_final)

    df = safe_read_csv(input_csv)
    mask_missing = df["macroarea"].isna() | df["macroarea"].astype(str).str.strip().eq("")
    pendientes = df.loc[mask_missing].copy()
    if args.limite > 0:
        pendientes = pendientes.head(args.limite)

    ya = set()
    rows: list[dict] = []
    logs: list[dict] = []
    if not args.reiniciar and output_csv.exists():
        prev = safe_read_csv(output_csv)
        rows = prev.to_dict("records")
        if "unidad_id" in prev.columns:
            ya = set(prev["unidad_id"].dropna().astype(str))
    if not args.reiniciar and output_log.exists():
        prev_log = safe_read_csv(output_log)
        logs = prev_log.to_dict("records")

    pendientes = pendientes[~pendientes["unidad_id"].astype(str).isin(ya)].copy()
    if pendientes.empty:
        final_df = construir_salida_final(df, pd.DataFrame(rows))
        final_df.to_csv(str(output_final), sep=";", encoding="utf-8-sig", index=False)
        guardar_tabla_y_reporte(final_df)
        print("No hay casos pendientes de deducción de macroárea.")
        return

    cliente = genai.Client(api_key=cargar_api_key())

    for i, (_, row) in enumerate(pendientes.iterrows(), 1):
        unidad_id = str(row["unidad_id"])
        nombre = str(row.get("nombre_archivo_pdf", ""))
        try:
            res = analizar_con_gemini(cliente, row, args.modelo)
            rows.append(
                {
                    "unidad_id": unidad_id,
                    "nombre_archivo_pdf": nombre,
                    "macroarea_deducida": res.macroarea_deducida,
                    "nivel_confianza_macroarea": res.nivel_confianza_macroarea,
                    "justificacion_macroarea": res.justificacion_macroarea,
                }
            )
            logs.append(
                {
                    "unidad_id": unidad_id,
                    "nombre_archivo_pdf": nombre,
                    "estado": "OK",
                    "macroarea_deducida": res.macroarea_deducida,
                    "timestamp": datetime.now().isoformat(),
                }
            )
            print(f"[{i}/{len(pendientes)}] {nombre} -> {res.macroarea_deducida}")
        except Exception as e:
            msg = str(e)
            if es_error_de_cuota(msg):
                ok = False
                ultimo = msg
                for _ in range(args.reintentos_429):
                    print(f"[{i}/{len(pendientes)}] {nombre} -> cuota/rate limit, espera {args.espera_429}s")
                    time.sleep(args.espera_429)
                    try:
                        res = analizar_con_gemini(cliente, row, args.modelo)
                        rows.append(
                            {
                                "unidad_id": unidad_id,
                                "nombre_archivo_pdf": nombre,
                                "macroarea_deducida": res.macroarea_deducida,
                                "nivel_confianza_macroarea": res.nivel_confianza_macroarea,
                                "justificacion_macroarea": res.justificacion_macroarea,
                            }
                        )
                        logs.append(
                            {
                                "unidad_id": unidad_id,
                                "nombre_archivo_pdf": nombre,
                                "estado": "OK (reintento)",
                                "macroarea_deducida": res.macroarea_deducida,
                                "timestamp": datetime.now().isoformat(),
                            }
                        )
                        ok = True
                        break
                    except Exception as e2:
                        ultimo = str(e2)
                        if not es_error_de_cuota(ultimo):
                            break
                if not ok:
                    logs.append(
                        {
                            "unidad_id": unidad_id,
                            "nombre_archivo_pdf": nombre,
                            "estado": f"ERROR: {ultimo}",
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    guardar(rows, logs, output_csv, output_log)
                    final_df = construir_salida_final(df, pd.DataFrame(rows))
                    final_df.to_csv(str(output_final), sep=";", encoding="utf-8-sig", index=False)
                    guardar_tabla_y_reporte(final_df)
                    if args.cortar_en_cuota:
                        print("Corte limpio por cuota agotada.")
                        return
            else:
                logs.append(
                    {
                        "unidad_id": unidad_id,
                        "nombre_archivo_pdf": nombre,
                        "estado": f"ERROR: {msg}",
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        if i % GUARDAR_CADA == 0:
            guardar(rows, logs, output_csv, output_log)
            final_df = construir_salida_final(df, pd.DataFrame(rows))
            final_df.to_csv(str(output_final), sep=";", encoding="utf-8-sig", index=False)
            guardar_tabla_y_reporte(final_df)
        time.sleep(DELAY_SEG)

    guardar(rows, logs, output_csv, output_log)
    final_df = construir_salida_final(df, pd.DataFrame(rows))
    final_df.to_csv(str(output_final), sep=";", encoding="utf-8-sig", index=False)
    guardar_tabla_y_reporte(final_df)
    print(f"Deducción guardada en: {output_csv}")
    print(f"Lista final con macroárea: {output_final}")
    print(f"Tabla por área: {OUT_TABLE}")
    print(f"Reporte: {OUT_REPORT}")


if __name__ == "__main__":
    main()
