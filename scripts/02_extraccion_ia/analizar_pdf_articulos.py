"""
analizar_pdf_articulos.py
=========================
Lee cada PDF descargado y extrae un anÃ¡lisis metodolÃ³gico completo
usando Gemini (Google AI Studio) con salida estructurada (Pydantic).

Campos extraÃ­dos por artÃ­culo (v4):
  nombre_archivo, disciplina, objetivo_general,
  frase_inferencia, frase_muestreo,
  tipo_estudio, enfoque_metodologico, diseno_estudio, tamano_muestra,
  es_cuantitativo_con_inferencia, muestreo_probabilistico,
  muestreo_no_probabilistico, declara_tipo_muestreo,
  declara_calculo_tamano_muestral, reporta_intervalos_confianza,
  extrapola_a_poblacion, advierte_limites_muestreo,
  aplica_muestreo_inferencial, clasificacion_inferencial,
  motivo_principal, nivel_confianza_clasificacion,
  software_estadistico, comentario_metodologico

Salidas:
  base_auditoria.csv    â€" una fila por artÃ­culo (separador ;)
  base_auditoria.xlsx   â€" Ã­dem + hojas de resumen
  auditoria_log.csv     â€" estado por archivo (OK / ERROR / OMITIDO)

CaracterÃ­sticas:
  - Guarda progreso incremental cada GUARDAR_CADA artÃ­culos
  - Reanuda desde donde quedÃ³ (omite PDFs ya procesados)
  - Trunca texto largo para no exceder contexto del modelo
  - Rate-limit seguro: pausa configurable entre llamadas

Uso:
    python analizar_pdf_articulos.py
    python analizar_pdf_articulos.py --carpeta "ruta/a/pdfs"
    python analizar_pdf_articulos.py --carpeta "ruta/a/pdfs" --reiniciar
    python analizar_pdf_articulos.py --seleccion-csv "calibracion_v4_piloto.csv"
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import re
from datetime import datetime
from pathlib import Path

# Forzar UTF-8 en stdout/stderr para evitar errores en consolas Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import pdfplumber
from pydantic import BaseModel, Field

# â"€â"€ Rutas â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
BASE_DIR     = Path(__file__).resolve().parent
PDF_DIR      = BASE_DIR / "pdfs_articulos"
OUT_CSV      = BASE_DIR / "base_auditoria.csv"
OUT_XLSX     = BASE_DIR / "base_auditoria.xlsx"
OUT_LOG      = BASE_DIR / "auditoria_log.csv"

# â"€â"€ ConfiguraciÃ³n â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
MODELO_DEFAULT  = "gemini-2.5-flash"
MODELO          = MODELO_DEFAULT
MAX_CHARS_PDF   = 30_000        # Gemini Flash tiene contexto enorme â€" aprovechamos mÃ¡s texto
GUARDAR_CADA    = 10            # guardar CSV cada N artÃ­culos procesados
DELAY_SEG       = 0.5           # Gemini Flash es rÃ¡pido y barato
PROMPT_EXTRA    = ""

# â"€â"€ Schema Pydantic â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

class AnalisisArticulo(BaseModel):
    """Resultado del anÃ¡lisis metodolÃ³gico de un artÃ­culo cientÃ­fico."""

    disciplina: str = Field(
        default="",
        description="Ãrea disciplinaria del artÃ­culo (ej: Medicina, PsicologÃ­a, AgronomÃ­a)"
    )
    objetivo_general: str = Field(
        default="",
        description="Objetivo principal del estudio en una oraciÃ³n"
    )
    frase_inferencia: str = Field(
        default="",
        description="Cita textual del artÃ­culo relacionada con inferencia estadÃ­stica. "
                    "'N/A' si no hay inferencia."
    )
    frase_muestreo: str = Field(
        default="",
        description="Cita textual del artÃ­culo relacionada con muestreo o selecciÃ³n de muestra. "
                    "'N/A' si no se menciona."
    )
    tipo_estudio: str = Field(
        default="",
        description="Tipo de estudio (ej: Descriptivo, Experimental, Cuasiexperimental, "
                    "Correlacional, RevisiÃ³n sistemÃ¡tica, Reporte de caso)"
    )
    enfoque_metodologico: str = Field(
        default="",
        description="Cuantitativo | Cualitativo | Mixto | No aplica"
    )
    diseno_estudio: str = Field(
        default="",
        description="DiseÃ±o especÃ­fico (ej: corte transversal, cohorte, caso-control, "
                    "ensayo controlado aleatorizado, propuesta/desarrollo)"
    )
    tamano_muestra: str = Field(
        default="",
        description="TamaÃ±o de muestra declarado (nÃºmero o descripciÃ³n). "
                    "'No declara' si no se menciona."
    )
    es_cuantitativo_con_inferencia: str = Field(
        default="",
        description="SÃ­ | No â€" Â¿El artÃ­culo aplica estadÃ­stica inferencial "
                    "(pruebas de hipÃ³tesis, IC, regresiÃ³n, ANOVA, etc.)?"
    )
    muestreo_probabilistico: str = Field(
        default="",
        description="SÃ­ | No | No aplica â€" Â¿Usa muestreo aleatorio o probabilÃ­stico?"
    )
    muestreo_no_probabilistico: str = Field(
        default="",
        description="SÃ­ | No | No aplica â€" Â¿Usa muestreo por conveniencia, intencional, "
                    "bola de nieve u otro no probabilÃ­stico?"
    )
    declara_tipo_muestreo: str = Field(
        default="",
        description="SÃ­ | No â€" Â¿El artÃ­culo declara explÃ­citamente el tipo de muestreo utilizado?"
    )
    declara_calculo_tamano_muestral: str = Field(
        default="",
        description="SÃ­ | No â€" Â¿El artÃ­culo justifica o calcula el tamaÃ±o muestral?"
    )
    reporta_intervalos_confianza: str = Field(
        default="",
        description="SÃ­ | No â€" Â¿Reporta intervalos de confianza (IC)?"
    )
    extrapola_a_poblacion: str = Field(
        default="",
        description="SÃ­ | No â€" Â¿Generaliza o extrapola resultados explÃ­citamente a una poblaciÃ³n?"
    )
    advierte_limites_muestreo: str = Field(
        default="",
        description="SÃ­ | No â€" Â¿Advierte sobre limitaciones debidas al tipo de muestreo?"
    )
    aplica_muestreo_inferencial: str = Field(
        default="",
        description="SÃ­ | No â€" indica si el artÃ­culo pertenece al universo analÃ­tico "
                    "de una auditorÃ­a de muestreo inferencial."
    )
    clasificacion_inferencial: str = Field(
        default="",
        description="Falla fuerte | Debilidad importante | Sin falla relevante | No aplica"
    )
    motivo_principal: str = Field(
        default="",
        description="Motivo principal de la clasificaciÃ³n. Ejemplos: Muestra no probabilÃ­stica "
                    "con inferencia amplia, Tipo de muestreo no declarado, TamaÃ±o muestral no "
                    "justificado, Censo/universo completo, Serie temporal/panel exhaustivo, "
                    "Meta-anÃ¡lisis/revisiÃ³n sistemÃ¡tica."
    )
    nivel_confianza_clasificacion: str = Field(
        default="",
        description="Alta | Media | Baja"
    )
    software_estadistico: str = Field(
        default="",
        description="Nombre del software estadÃ­stico declarado (ej: SPSS, R, Python, Stata). "
                    "'No declara' si no se menciona."
    )
    comentario_metodologico: str = Field(
        default="",
        description="Texto breve (2-4 oraciones) con el juicio final sobre la elegibilidad y la "
                    "calidad inferencial del artÃ­culo. Debe referenciar evidencias concretas."
    )


# â"€â"€ Prompt del sistema â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

SYSTEM_PROMPT = """Eres un metodólogo experto en investigación científica cuantitativa.
Tu tarea es clasificar artículos científicos según fallas en diseño muestral e inferencia estadística.
Debes clasificar cada artículo en dos pasos.

PASO 1. ELEGIBILIDAD
Decide si el artículo pertenece al universo analítico de una auditoría de muestreo inferencial.

Usa aplica_muestreo_inferencial = "Sí" solo si:
  - el artículo usa inferencia estadística;
  - y existe una pregunta real sobre muestreo o base inferencial de unidades observacionales
    relevantes para una población objetivo humana o animal en sentido epidemiológico/social.

Usa aplica_muestreo_inferencial = "No" cuando el artículo sea:
  - Meta-análisis, revisiones sistemáticas, umbrella reviews.
  - Series temporales o paneles exhaustivos sin problema muestral clásico.
  - Experimentos de laboratorio, in vitro, ex vivo o con animales de laboratorio.
  - Artículos teóricos, matemáticos, simulaciones, benchmarking de modelos/algoritmos.
  - Estudios de caso históricos, arqueológicos, textuales o de cultura material.
  - Estudios ecológicos de campo, monitoreo de fauna/flora, transectos ambientales,
    análisis de biodiversidad o censos ecológicos donde el muestreo es el estándar
    del campo y no representa personas u organizaciones.
  - Estudios de validación de instrumentos psicométricos o escalas cuyo objetivo
    principal es demostrar validez/confiabilidad, no describir una población.
  - Estudios de tecnología de alimentos, microbiología, bromatología, análisis sensorial
    con paneles de catadores o análisis de productos, donde la muestra es el producto.
  - Estudios traslacionales, preclínicos o mecanísticos con modelos animales, tejidos,
    organoides o muestras clínicas de laboratorio cuya conclusión principal es biológica.
  - Artículos con datos censales o registros administrativos que cubren toda la población.

PASO 2. CLASIFICACIÓN PRINCIPAL
Solo si aplica_muestreo_inferencial = "Sí", clasifica usando la siguiente regla de tres condiciones.

═══════════════════════════════════════════════════════════════
FALLA FUERTE — requiere las TRES condiciones simultáneamente:
  [A] Muestreo no probabilístico (conveniencia, voluntarios, consecutivo, intencional,
      bola de nieve) SIN que los autores adviertan sobre el sesgo o limitaciones de ese
      muestreo en ninguna parte del texto (métodos, discusión o limitaciones).
  [B] Extrapolación explícita: los autores generalizan resultados a una población más amplia
      (ciudad, país, profesión, grupo etario) sin justificación probabilística.
  [C] Análisis estadístico inferencial aplicado (pruebas de hipótesis, regresión, ANOVA,
      chi-cuadrado) que asume representatividad que la muestra no tiene.

  REGLA ABSOLUTA: Si los autores reconocen EN CUALQUIER PARTE DEL TEXTO que la muestra
  es no probabilística, tiene limitaciones de representatividad, o que los resultados no
  son generalizables → condición [A] NO se cumple → NO puede ser Falla fuerte.
  En ese caso, la clasificación máxima es Debilidad importante.
═══════════════════════════════════════════════════════════════

DEBILIDAD IMPORTANTE — cuando hay problemas metodológicos reales pero NO se cumplen
las tres condiciones de Falla fuerte simultáneamente. Incluye:
  - Muestreo no probabilístico con reconocimiento explícito de limitaciones, incluso si
    hay extrapolación moderada o implícita en la discusión.
  - No declara tipo de muestreo o no justifica tamaño muestral, pero sin extrapolación fuerte.
  - Muestra no probabilística en estudio preliminar, exploratorio o contextual.
  - Artículo con cautela parcial en conclusiones aunque insuficiente.
  - Estudio descriptivo con base muestral imperfecta pero lenguaje final moderado.
  - Diseño cuasi-experimental sin aleatorización pero conclusiones acotadas.
  - Contexto latinoamericano con recursos limitados: muestras pequeñas justificadas
    por acceso/recursos, sin generalización fuerte → Debilidad importante, no Falla fuerte.

SIN FALLA RELEVANTE — cuando:
  - Muestreo probabilístico (aleatorio simple, estratificado, sistemático, conglomerados).
  - Uso de bases de datos nacionales/regionales representativas o censos.
  - Diseño experimental controlado con asignación aleatoria a grupos.
  - Estudio descriptivo que no generaliza más allá del grupo observado.
  - Limitaciones del muestreo claramente reconocidas Y conclusiones explícitamente
    acotadas al grupo estudiado sin ninguna extrapolación.
  - Artículo cualitativo (entrevistas, etnografía, análisis del discurso): no busca
    representatividad estadística → Sin falla relevante.

REGLAS DE DECISIÓN:
  1. REGLA PRINCIPAL: advierte_limites_muestreo = "Sí" → nunca Falla fuerte → máximo DI.
  2. Si la extrapolación es solo implícita o moderada (lenguaje prudente) → DI, no FF.
  3. En duda entre FF y DI → siempre preferir DI.
  4. En duda entre DI y SFR → usar evidencia textual y marcar confianza Media/Baja.
  5. Si aplica_muestreo_inferencial = "No" → clasificacion_inferencial = "No aplica".
  6. No penalizar tamaño muestral pequeño si el muestreo es apropiado para el campo.

INTERPRETACIÓN DE CAMPOS AUXILIARES:
  - extrapola_a_poblacion = "Sí" solo si el texto hace afirmación poblacional EXPLÍCITA
    que excede la muestra (ej: "los estudiantes universitarios presentan...", "la prevalencia
    en la región es..."). NO marcar "Sí" por recomendaciones de estudios futuros o
    sugerencias de política sin afirmación directa.
  - muestreo_no_probabilistico = "Sí" si el artículo lo declara o si el texto muestra
    claramente reclutamiento por conveniencia, accesibilidad, voluntariado o selección
    intencional.
  - advierte_limites_muestreo = "Sí" si el artículo reconoce EN CUALQUIER PARTE limitaciones
    de representatividad, generalización o sesgo muestral, aunque sea brevemente.

Responde SOLO con el JSON estructurado solicitado, sin texto adicional."""


def construir_prompt(texto_pdf: str, nombre_archivo: str) -> str:
    return f"""Analiza el siguiente artÃ­culo cientÃ­fico y extrae la informaciÃ³n metodolÃ³gica solicitada.

Archivo: {nombre_archivo}

--- TEXTO DEL ARTÃCULO ---
{texto_pdf}
--- FIN DEL TEXTO ---

Responde con el JSON estructurado con los campos definidos en el esquema.
Si alguna informaciÃ³n no estÃ¡ disponible en el texto, indica 'No disponible' o 'No declara'
segÃºn corresponda al campo.
Antes de decidir, verifica explícitamente estas preguntas:
1. ¿El artículo entra al universo de auditoría? (descarta lab, ecología, validación, censos)
2. ¿El muestreo es no probabilístico?
3. CRÍTICO: ¿Los autores reconocen en ALGUNA PARTE limitaciones de representatividad o sesgo?
   Si la respuesta es SÍ → la clasificación máxima es Debilidad importante, nunca Falla fuerte.
4. ¿Hay extrapolación EXPLÍCITA a una población más amplia (no solo recomendaciones)?
5. ¿Se aplica inferencia estadística que asume representatividad?
   Solo si las tres condiciones anteriores (no-probabilístico + sin advertencia + extrapolación)
   se cumplen simultáneamente → Falla fuerte.
6. ¿El contexto es latinoamericano con recursos limitados? → mayor tolerancia a DI.
7. ¿Existe evidencia suficiente para clasificar como Sin falla relevante?
Usa el criterio v4.1-NTK calibrado con NotebookLM.
{PROMPT_EXTRA}"""


def derivar_incumple_legacy(aplica: str, clasificacion: str) -> str:
    """Mantiene compatibilidad con la variable histÃ³rica SÃ­/No/No aplica."""
    aplica = (aplica or "").strip()
    clasificacion = (clasificacion or "").strip()
    if aplica == "No" or clasificacion == "No aplica":
        return "No aplica"
    if clasificacion == "Falla fuerte":
        return "SÃ­"
    if clasificacion in {"Debilidad importante", "Sin falla relevante"}:
        return "No"
    return "No aplica"


def cargar_seleccion_csv(path: Path) -> list[dict]:
    """Carga una selecciÃ³n explÃ­cita de PDFs desde CSV."""
    seleccion: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            nombre = (row.get("nombre_archivo") or "").strip()
            ruta_pdf = (row.get("ruta_pdf") or "").strip()
            if nombre or ruta_pdf:
                seleccion.append({
                    "nombre_archivo": nombre,
                    "ruta_pdf": ruta_pdf,
                })
    return seleccion


def es_error_de_cuota(msg: str) -> bool:
    """Detecta errores de cuota/rate limit para decidir reintentos o corte limpio."""
    m = (msg or "").lower()
    return (
        "429" in m
        or "quota" in m
        or "rate limit" in m
        or "resource_exhausted" in m
        or "exceeded your current quota" in m
    )


# â"€â"€ ExtracciÃ³n de texto del PDF â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

def extraer_texto_pdf(ruta_pdf: Path, max_chars: int = MAX_CHARS_PDF) -> tuple[str, str]:
    """
    Extrae texto del PDF con pdfplumber.
    Retorna (texto, advertencia).
    """
    try:
        texto_paginas = []
        with pdfplumber.open(str(ruta_pdf)) as pdf:
            n_paginas = len(pdf.pages)
            for i, pagina in enumerate(pdf.pages):
                t = pagina.extract_text()
                if t:
                    texto_paginas.append(t)
                # Cortar si ya tenemos suficiente
                if sum(len(p) for p in texto_paginas) >= max_chars:
                    break

        texto_completo = "\n".join(texto_paginas)

        if not texto_completo.strip():
            return "", "PDF sin texto extraÃ­ble (posiblemente escaneado)"

        advertencia = ""
        if len(texto_completo) > max_chars:
            texto_completo = texto_completo[:max_chars]
            advertencia = f"Truncado a {max_chars} chars (original: {n_paginas} pÃ¡g.)"

        return texto_completo, advertencia

    except Exception as e:
        return "", f"Error al leer PDF: {e}"


# â"€â"€ Llamada a Gemini API â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

def analizar_con_gemini(
    api_key: str,
    texto_pdf: str,
    nombre_archivo: str,
) -> AnalisisArticulo:
    """EnvÃ­a el texto a Gemini vÃ­a REST con curl y retorna el anÃ¡lisis estructurado."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODELO}:generateContent?key={api_key}"
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            SYSTEM_PROMPT
                            + "\n\n"
                            + construir_prompt(texto_pdf, nombre_archivo)
                            + "\n\nResponde exclusivamente con JSON vÃ¡lido."
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0,
            "responseMimeType": "application/json",
        },
    }

    ultimo_error = ""
    payload_path: Path | None = None
    try:
        # En Windows, pasar JSON grande con "-d <json>" puede superar el límite de
        # longitud de línea de comandos (WinError 206). Se usa archivo temporal.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as tmp:
            json.dump(payload, tmp, ensure_ascii=False)
            payload_path = Path(tmp.name)

        cmd = [
            "curl",
            "--max-time",
            "180",
            "--retry",
            "3",
            "--retry-all-errors",
            "--retry-delay",
            "5",
            "--retry-max-time",
            "180",
            "-sS",
            "-X",
            "POST",
            url,
            "-H",
            "Content-Type: application/json",
            "--data-binary",
            f"@{payload_path}",
        ]

        for intento in range(1, 5):
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            if result.returncode == 0:
                data = extraer_primer_json_objeto(result.stdout)
                if "error" in data:
                    raise RuntimeError(json.dumps(data["error"], ensure_ascii=False))

                text = data["candidates"][0]["content"]["parts"][0]["text"]
                parsed = parsear_json_tolerante(text)
                if isinstance(parsed, list):
                    if not parsed:
                        raise RuntimeError("Gemini devolvió una lista JSON vacía")
                    parsed = parsed[0]
                if not isinstance(parsed, dict):
                    raise RuntimeError(
                        f"Gemini devolvió JSON con tipo inesperado: {type(parsed).__name__}"
                    )
                return AnalisisArticulo.model_validate(parsed)

            ultimo_error = result.stderr.strip() or f"curl exited with code {result.returncode}"
            error_normalizado = ultimo_error.lower()
            if intento < 4 and (
                result.returncode in {6, 7, 28}
                or "could not resolve host" in error_normalizado
                or "timed out" in error_normalizado
                or "failed to connect" in error_normalizado
            ):
                time.sleep(5 * intento)
                continue
            raise RuntimeError(ultimo_error)

        raise RuntimeError(ultimo_error or "curl falló sin detallar el motivo")
    finally:
        if payload_path and payload_path.exists():
            try:
                payload_path.unlink()
            except OSError:
                pass


def parsear_json_tolerante(texto: str):
    """
    Intenta parsear JSON incluso si el modelo agrega envoltorios de texto
    o bloques markdown alrededor del objeto.
    """
    if texto is None:
        raise RuntimeError("Gemini devolvió contenido vacío")

    bruto = str(texto).strip()
    if not bruto:
        raise RuntimeError("Gemini devolvió contenido vacío")

    # 1) Camino directo.
    try:
        return json.loads(bruto)
    except json.JSONDecodeError:
        pass

    # 2) Remover fences markdown ```json ... ```
    fence = re.search(r"```(?:json)?\s*(.*?)\s*```", bruto, flags=re.IGNORECASE | re.DOTALL)
    if fence:
        candidato = fence.group(1).strip()
        try:
            return json.loads(candidato)
        except json.JSONDecodeError:
            pass

    # 3) Intentar extraer el bloque entre la primera llave/corchete y la última.
    ini_obj = bruto.find("{")
    fin_obj = bruto.rfind("}")
    if ini_obj != -1 and fin_obj != -1 and fin_obj > ini_obj:
        candidato = bruto[ini_obj:fin_obj + 1].strip()
        try:
            return json.loads(candidato)
        except json.JSONDecodeError:
            pass

    ini_arr = bruto.find("[")
    fin_arr = bruto.rfind("]")
    if ini_arr != -1 and fin_arr != -1 and fin_arr > ini_arr:
        candidato = bruto[ini_arr:fin_arr + 1].strip()
        try:
            return json.loads(candidato)
        except json.JSONDecodeError:
            pass

    raise RuntimeError("No se pudo parsear JSON de la respuesta de Gemini")


def extraer_primer_json_objeto(texto: str) -> dict:
    """
    Extrae un objeto JSON desde una salida que pueda incluir ruido antes/después.
    """
    bruto = (texto or "").strip()
    if not bruto:
        raise RuntimeError("Respuesta vacía de curl")

    try:
        data = json.loads(bruto)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    ini = bruto.find("{")
    fin = bruto.rfind("}")
    if ini != -1 and fin != -1 and fin > ini:
        candidato = bruto[ini:fin + 1]
        try:
            data = json.loads(candidato)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass

    raise RuntimeError("No se pudo parsear JSON de respuesta de API")


# â"€â"€ ConstrucciÃ³n de fila DataFrame â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

def resultado_a_fila(
    nombre_archivo: str,
    analisis: AnalisisArticulo,
    meta: dict,
) -> dict:
    """Combina metadata del CSV base con los campos extraÃ­dos por Gemini."""
    fila = {
        # IdentificaciÃ³n (de base_articulos_muestra.csv)
        "nombre_archivo":   nombre_archivo,
        "id_revista":       meta.get("id_revista", ""),
        "revista":          meta.get("revista", ""),
        "pais":             meta.get("pais", ""),
        "macroarea":        meta.get("macroarea", ""),
        "metodologia":      meta.get("metodologia", ""),
        "titulo":           meta.get("titulo", ""),
        "anio":             meta.get("anio", ""),
        "autores":          meta.get("autores", ""),
        "doi":              meta.get("doi", ""),
        "url_fulltext":     meta.get("url_fulltext", ""),
        # Campos extraÃ­dos por Gemini
        "disciplina":                       analisis.disciplina,
        "objetivo_general":                 analisis.objetivo_general,
        "frase_inferencia":                 analisis.frase_inferencia,
        "frase_muestreo":                   analisis.frase_muestreo,
        "tipo_estudio":                     analisis.tipo_estudio,
        "enfoque_metodologico":             analisis.enfoque_metodologico,
        "diseno_estudio":                   analisis.diseno_estudio,
        "tamano_muestra":                   analisis.tamano_muestra,
        "es_cuantitativo_con_inferencia":   analisis.es_cuantitativo_con_inferencia,
        "muestreo_probabilistico":          analisis.muestreo_probabilistico,
        "muestreo_no_probabilistico":       analisis.muestreo_no_probabilistico,
        "declara_tipo_muestreo":            analisis.declara_tipo_muestreo,
        "declara_calculo_tamano_muestral":  analisis.declara_calculo_tamano_muestral,
        "reporta_intervalos_confianza":     analisis.reporta_intervalos_confianza,
        "extrapola_a_poblacion":            analisis.extrapola_a_poblacion,
        "advierte_limites_muestreo":        analisis.advierte_limites_muestreo,
        "aplica_muestreo_inferencial":      analisis.aplica_muestreo_inferencial,
        "clasificacion_inferencial":        analisis.clasificacion_inferencial,
        "motivo_principal":                 analisis.motivo_principal,
        "nivel_confianza_clasificacion":    analisis.nivel_confianza_clasificacion,
        "incumple_inferencia":              derivar_incumple_legacy(
                                                analisis.aplica_muestreo_inferencial,
                                                analisis.clasificacion_inferencial,
                                            ),
        "software_estadistico":             analisis.software_estadistico,
        "comentario_metodologico":          analisis.comentario_metodologico,
    }
    return fila


# â"€â"€ Guardar resultados â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

def guardar(filas: list[dict], log_filas: list[dict], out_csv: Path, out_log: Path) -> None:
    """Guarda CSV de resultados y log."""
    if filas:
        df = pd.DataFrame(filas)
        df.index = range(1, len(df) + 1)
        df.index.name = "nro"
        df.to_csv(out_csv, encoding="utf-8-sig", sep=";")

    if log_filas:
        pd.DataFrame(log_filas).to_csv(out_log, encoding="utf-8-sig", sep=";", index=False)


def guardar_excel(filas: list[dict], log_filas: list[dict], out_xlsx: Path) -> None:
    """Genera Excel con hojas de resumen."""
    if not filas:
        return
    try:
        df = pd.DataFrame(filas)
        df.index = range(1, len(df) + 1)
        df.index.name = "nro"
        df_log = pd.DataFrame(log_filas)

        with pd.ExcelWriter(out_xlsx, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Auditoria", index=True)
            df_log.to_excel(writer, sheet_name="Log", index=False)

            if "clasificacion_inferencial" in df.columns:
                res = df["clasificacion_inferencial"].value_counts().reset_index()
                res.columns = ["clasificacion_inferencial", "n"]
                res["pct"] = (res["n"] / len(df) * 100).round(1)
                res.to_excel(writer, sheet_name="Resumen_clasificacion", index=False)

            if "aplica_muestreo_inferencial" in df.columns:
                res_ap = df["aplica_muestreo_inferencial"].value_counts().reset_index()
                res_ap.columns = ["aplica_muestreo_inferencial", "n"]
                res_ap["pct"] = (res_ap["n"] / len(df) * 100).round(1)
                res_ap.to_excel(writer, sheet_name="Resumen_aplicabilidad", index=False)

            if "macroarea" in df.columns and "clasificacion_inferencial" in df.columns:
                aplic = df[df["aplica_muestreo_inferencial"] == "SÃ­"]
                if not aplic.empty:
                    res2 = aplic.groupby("macroarea").agg(
                        n_aplicable=("titulo", "count"),
                        n_falla_fuerte=("clasificacion_inferencial", lambda x: (x == "Falla fuerte").sum()),
                        n_debilidad_o_falla=("clasificacion_inferencial", lambda x: x.isin(["Falla fuerte", "Debilidad importante"]).sum()),
                    ).reset_index()
                    res2["pct_falla_fuerte"] = (res2["n_falla_fuerte"] / res2["n_aplicable"] * 100).round(1)
                    res2["pct_debilidad_o_falla"] = (res2["n_debilidad_o_falla"] / res2["n_aplicable"] * 100).round(1)
                    res2.to_excel(writer, sheet_name="Resumen_macroarea_v4", index=False)

            # Hoja legacy para comparabilidad histÃ³rica
            if "incumple_inferencia" in df.columns:
                res_legacy = df["incumple_inferencia"].value_counts().reset_index()
                res_legacy.columns = ["incumple_inferencia", "n"]
                res_legacy["pct"] = (res_legacy["n"] / len(df) * 100).round(1)
                res_legacy.to_excel(writer, sheet_name="Resumen_legacy", index=False)

        print(f"  Excel guardado: {out_xlsx}")
    except Exception as e:
        print(f"  Excel no generado: {e}")


# â"€â"€ Main â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--carpeta",   default=str(PDF_DIR), help="Carpeta con PDFs")
    parser.add_argument("--reiniciar", action="store_true",  help="Reprocesar todo (ignora progreso)")
    parser.add_argument("--desde",     type=int, default=0,  help="Ãndice de inicio (0-based) en lista de PDFs ordenados")
    parser.add_argument("--hasta",     type=int, default=0,  help="Ãndice de fin exclusivo (0=hasta el final)")
    parser.add_argument("--sufijo",    default="",           help="Sufijo para archivos de salida (ej: _p2 â†’ base_auditoria_p2.csv)")
    parser.add_argument("--seleccion-csv", default="",       help="CSV con columna nombre_archivo para procesar un subconjunto explÃ­cito")
    parser.add_argument("--modelo",    default="",           help="Modelo Gemini a usar (ej: gemini-1.5-flash)")
    parser.add_argument("--reintentos-429", type=int, default=1, help="Reintentos extra ante 429/quota")
    parser.add_argument("--espera-429", type=int, default=60, help="Segundos de espera entre reintentos por 429/quota")
    parser.add_argument("--cortar-en-cuota", action="store_true", help="Detiene la corrida al agotar reintentos por cuota")
    parser.add_argument("--criterio-conservador", action="store_true", help="Aplica criterio conservador para reducir sobreclasificacion de fallas")
    parser.add_argument("--forzar-aplicable", action="store_true", help="Trata la seleccion como universo aplicable; evita usar 'No aplica' salvo evidencia extrema")
    args = parser.parse_args()

    # Permitir override de modelo por CLI o variable de entorno
    global MODELO
    MODELO = (
        args.modelo
        or os.environ.get("GEMINI_MODEL")
        or os.environ.get("GOOGLE_MODEL")
        or MODELO_DEFAULT
    )

    global PROMPT_EXTRA
    extras: list[str] = []
    if args.criterio_conservador:
        extras.append(
            "CRITERIO ADICIONAL DE MATERIALIDAD: clasifica como 'Falla fuerte' solo si la "
            "debilidad muestral probablemente cambia de forma sustantiva la validez de la "
            "conclusion principal (direccion o magnitud). Si el problema afecta principalmente "
            "el reporte, la precision o el alcance, prefiere 'Debilidad importante' o "
            "'Sin falla relevante'."
        )
    if args.forzar_aplicable:
        extras.append(
            "ESTE LOTE YA FUE PRESELECCIONADO COMO APLICABLE. No uses 'No aplica' salvo "
            "evidencia inequívoca de que no existe inferencia muestral; en caso de duda, "
            "elige entre 'Debilidad importante' y 'Sin falla relevante'."
        )
    PROMPT_EXTRA = "\n".join(extras).strip()

    # Salidas con sufijo para ejecuciones paralelas
    out_csv  = BASE_DIR / f"base_auditoria{args.sufijo}.csv"
    out_xlsx = BASE_DIR / f"base_auditoria{args.sufijo}.xlsx"
    out_log  = BASE_DIR / f"auditoria_log{args.sufijo}.csv"

    carpeta_pdfs = Path(args.carpeta)

    print("=" * 72)
    print("  AUDITORÃA METODOLÃ"GICA DE ARTÃCULOS â€" GEMINI")
    print(f"  Modelo : {MODELO}  |  Sufijo: '{args.sufijo}' | Rango: [{args.desde}:{args.hasta or 'fin'}]")
    print(f"  Carpeta: {carpeta_pdfs}")
    print(f"  Fecha  : {datetime.today().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 72)

    if not carpeta_pdfs.exists():
        print(f"\nâš  La carpeta no existe: {carpeta_pdfs}")
        return

    # â"€â"€ Cargar base de metadatos â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    meta_df = None
    base_csv = BASE_DIR / "base_articulos_muestra.csv"
    if base_csv.exists():
        meta_df = pd.read_csv(base_csv, sep=";", encoding="utf-8-sig", index_col="nro")
        print(f"  Metadatos cargados: {len(meta_df)} artÃ­culos en base_articulos_muestra.csv")

    # â"€â"€ Cargar progreso existente â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    ya_procesados: set[str] = set()
    filas_acumuladas: list[dict] = []
    log_acumulado: list[dict] = []

    if not args.reiniciar and out_csv.exists():
        df_prev = pd.read_csv(out_csv, sep=";", encoding="utf-8-sig")
        if "nombre_archivo" in df_prev.columns:
            ya_procesados = set(df_prev["nombre_archivo"].dropna())
            filas_acumuladas = df_prev.to_dict("records")
        if out_log.exists():
            df_log_prev = pd.read_csv(out_log, sep=";", encoding="utf-8-sig")
            log_acumulado = df_log_prev.to_dict("records")
        print(f"  Progreso anterior: {len(ya_procesados)} PDFs ya procesados")

    # â"€â"€ Obtener lista de PDFs (con rango opcional o selecciÃ³n explÃ­cita) â"€â"€â"€â"€â"€
    todos_pdfs = sorted(carpeta_pdfs.glob("*.pdf"))
    pdfs_por_nombre = {p.name: p for p in todos_pdfs}

    if args.seleccion_csv:
        seleccion_path = Path(args.seleccion_csv)
        if not seleccion_path.is_absolute():
            seleccion_path = BASE_DIR / seleccion_path
        seleccion = cargar_seleccion_csv(seleccion_path)
        faltantes: list[str] = []
        pdfs_rango: list[Path] = []
        for item in seleccion:
            ruta_pdf = item["ruta_pdf"]
            nombre = item["nombre_archivo"]
            pdf_path: Path | None = None

            if ruta_pdf:
                ruta_resuelta = Path(ruta_pdf)
                if not ruta_resuelta.is_absolute():
                    ruta_resuelta = (BASE_DIR.parent / ruta_resuelta).resolve()
                if ruta_resuelta.exists():
                    pdf_path = ruta_resuelta
                else:
                    faltantes.append(ruta_pdf)
                    continue
            elif nombre:
                if nombre in pdfs_por_nombre:
                    pdf_path = pdfs_por_nombre[nombre]
                else:
                    faltantes.append(nombre)
                    continue

            if pdf_path is not None:
                pdfs_rango.append(pdf_path)

        if faltantes:
            print(f"\nâš  PDFs de la selecciÃ³n no encontrados: {len(faltantes)}")
            for n in faltantes[:10]:
                print(f"   - {n}")
        print(f"  SelecciÃ³n explÃ­cita cargada desde: {seleccion_path}")
    else:
        fin = args.hasta if args.hasta > 0 else len(todos_pdfs)
        pdfs_rango = todos_pdfs[args.desde:fin]
    pendientes = [p for p in pdfs_rango if p.name not in ya_procesados]

    print(f"\n  PDFs en rango     : {len(pdfs_rango)} (de {len(todos_pdfs)} totales)")
    print(f"  Ya procesados     : {len(ya_procesados)}")
    print(f"  Pendientes        : {len(pendientes)}")

    if not pendientes:
        print("\n  Nada que procesar. Todos los PDFs ya tienen anÃ¡lisis.")
        guardar_excel(filas_acumuladas, log_acumulado, out_xlsx)
        return

    # â"€â"€ Inicializar cliente Gemini â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key and shutil.which("powershell"):
        # Intentar leer desde registro de Windows
        import subprocess
        result = subprocess.run(
            ["powershell", "-Command",
             "[System.Environment]::GetEnvironmentVariable('GOOGLE_API_KEY', 'User')"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        api_key = result.stdout.strip()
    if not api_key:
        raise ValueError("No se encontrÃ³ GOOGLE_API_KEY. ConfigÃºrala como variable de entorno.")
    total = len(pendientes)
    errores = 0
    corrida_interrumpida_por_cuota = False

    print(f"\n{'â"€'*72}")
    print(f"  {'#':>4}  {'Archivo':<50}  Estado")
    print(f"{'â"€'*72}")

    for i, ruta_pdf in enumerate(pendientes, 1):
        nombre = ruta_pdf.name
        estado = "OK"
        advertencia = ""

        try:
            # 1. Extraer texto
            texto, adv = extraer_texto_pdf(ruta_pdf)
            if adv:
                advertencia = adv

            if not texto:
                estado = f"SIN_TEXTO: {adv}"
                errores += 1
                log_acumulado.append({
                    "nombre_archivo": nombre, "estado": estado,
                    "advertencia": adv, "timestamp": datetime.now().isoformat()
                })
                print(f"  {i:>4}  {nombre:<50}  âš  {estado}")
                continue

            # 2. Buscar metadata en base_articulos_muestra usando nro del nombre de archivo
            meta = {}
            if meta_df is not None:
                m_nro = re.match(r"^(\d+)_", nombre)
                if m_nro:
                    nro_art = int(m_nro.group(1))
                    if nro_art in meta_df.index:
                        meta = meta_df.loc[nro_art].to_dict()

            # 3. Llamar a Gemini
            analisis = analizar_con_gemini(api_key, texto, nombre)

            # 4. Acumular resultado
            fila = resultado_a_fila(nombre, analisis, meta)
            filas_acumuladas.append(fila)

            if adv:
                estado = f"OK (truncado)"
            log_acumulado.append({
                "nombre_archivo": nombre, "estado": estado,
                "advertencia": adv,
                "aplica": analisis.aplica_muestreo_inferencial,
                "clasificacion": analisis.clasificacion_inferencial,
                "incumple": derivar_incumple_legacy(
                    analisis.aplica_muestreo_inferencial,
                    analisis.clasificacion_inferencial,
                ),
                "timestamp": datetime.now().isoformat()
            })

            # Indicador visual
            if analisis.clasificacion_inferencial == "Falla fuerte":
                icono = "ðŸ"´"
            elif analisis.clasificacion_inferencial == "Debilidad importante":
                icono = "ðŸŸ¡"
            elif analisis.clasificacion_inferencial == "Sin falla relevante":
                icono = "ðŸŸ¢"
            else:
                icono = "âšª"
            print(f"  {i:>4}  {nombre:<50}  {icono} {analisis.clasificacion_inferencial}")

        except Exception as e:
            msg = str(e)
            if "429" in msg or "quota" in msg.lower() or "rate" in msg.lower():
                print(f"  {i:>4}  {nombre:<50}  â³ Rate limit â€" esperando 60s")
                time.sleep(60)
                try:
                    analisis = analizar_con_gemini(api_key, texto, nombre)
                    fila = resultado_a_fila(nombre, analisis, meta)
                    filas_acumuladas.append(fila)
                    log_acumulado.append({
                        "nombre_archivo": nombre, "estado": "OK (reintento)",
                        "advertencia": "",
                        "aplica": analisis.aplica_muestreo_inferencial,
                        "clasificacion": analisis.clasificacion_inferencial,
                        "incumple": derivar_incumple_legacy(
                            analisis.aplica_muestreo_inferencial,
                            analisis.clasificacion_inferencial,
                        ),
                        "timestamp": datetime.now().isoformat()
                    })
                    print(f"  {i:>4}  {nombre:<50}  âœ… Reintento OK")
                    continue
                except Exception as e2:
                    errores += 1
                    estado = f"ERROR: {e2}"
                    log_acumulado.append({
                        "nombre_archivo": nombre, "estado": estado,
                        "advertencia": "", "timestamp": datetime.now().isoformat()
                    })
                    print(f"  {i:>4}  {nombre:<50}  âŒ {str(e2)[:50]}")
            else:
                errores += 1
                estado = f"ERROR: {e}"
                log_acumulado.append({
                    "nombre_archivo": nombre, "estado": estado,
                    "advertencia": "", "timestamp": datetime.now().isoformat()
                })
                print(f"  {i:>4}  {nombre:<50}  âŒ {str(e)[:50]}")

        # Guardar progreso incremental
        if i % GUARDAR_CADA == 0:
            guardar(filas_acumuladas, log_acumulado, out_csv, out_log)
            print(f"  {'â"€'*70}")
            print(f"  [Progreso guardado â€" {i}/{total}]")
            print(f"  {'â"€'*70}")

        time.sleep(DELAY_SEG)

    # â"€â"€ Guardado final â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    guardar(filas_acumuladas, log_acumulado, out_csv, out_log)
    guardar_excel(filas_acumuladas, log_acumulado, out_xlsx)

    # â"€â"€ Resumen â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€â"€
    print(f"\n{'='*72}")
    print("  RESUMEN FINAL")
    print(f"{'='*72}")
    print(f"  PDFs procesados    : {len(pendientes) - errores}")
    print(f"  Errores            : {errores}")
    print(f"  Total acumulado    : {len(filas_acumuladas)}")
    if corrida_interrumpida_por_cuota:
        print("  Estado corrida     : Interrumpida por cuota agotada")

    if filas_acumuladas:
        df_res = pd.DataFrame(filas_acumuladas)
        if "aplica_muestreo_inferencial" in df_res.columns:
            aplic = df_res[df_res["aplica_muestreo_inferencial"] == "SÃ­"]
            print(f"\n  Aplicables a auditorÃ­a     : {len(aplic)}")
            if not aplic.empty and "clasificacion_inferencial" in df_res.columns:
                n_fuerte = (aplic["clasificacion_inferencial"] == "Falla fuerte").sum()
                n_debil = (aplic["clasificacion_inferencial"] == "Debilidad importante").sum()
                print(f"  Falla fuerte               : {n_fuerte} ({n_fuerte/len(aplic)*100:.1f}%)")
                print(f"  Debilidad importante       : {n_debil} ({n_debil/len(aplic)*100:.1f}%)")

        print("\n  DistribuciÃ³n clasificacion_inferencial:")
        for val, cnt in df_res["clasificacion_inferencial"].value_counts().items():
            print(f"    {val:<22} {cnt:>5}  ({cnt/len(df_res)*100:.1f}%)")

        print("\n  DistribuciÃ³n legacy incumple_inferencia:")
        for val, cnt in df_res["incumple_inferencia"].value_counts().items():
            print(f"    {val:<15} {cnt:>5}  ({cnt/len(df_res)*100:.1f}%)")

    print(f"\n  CSV  : {out_csv}")
    print(f"  Excel: {out_xlsx}")
    print(f"  Log  : {out_log}")
    print("=" * 72)
    print("  Completado.")


if __name__ == "__main__":
    main()



