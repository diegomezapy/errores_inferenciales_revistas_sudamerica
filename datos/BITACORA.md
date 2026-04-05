# Bitácora del Proyecto — Fallas Inferenciales en Revistas Latinoamericanas

> **Actualizar este documento después de cada sesión de trabajo.**
> Formato: agregar nueva sección `## Sesión YYYY-MM-DD` al final.

---

## Contexto general del proyecto

**Objetivo:** Estimar la prevalencia de fallas inferenciales críticas en artículos científicos de revistas de América del Sur mediante un muestreo probabilístico multietápico.

**Repositorio principal:** `J:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO`
**Manuscrito LaTeX:** `G:\Mi unidad\DECENA_FACEN\03_TESIS\articulo_fallas_metodologicas\manuscrito\ARTICULO\`

---

## Sesión 2026-03-28

### Objetivo de la sesión
Construir un pipeline completo para generar una nueva muestra de revistas sudamericanas desde DOAJ, clasificarlas temáticamente y calcular el diseño muestral para una futura auditoría de fallas metodológicas.

---

### Paso 1 — Descarga del catálogo DOAJ

**Script:** [fetch_journals_sudamerica.py](fetch_journals_sudamerica.py)
**Hora:** 10:21
**Fuente:** `https://doaj.org/csv` (~21.000 revistas globales, dominio público CC0)

**Lógica:**
- Descarga el CSV completo de DOAJ
- Filtra los 12 países de América del Sur
- Traduce 35 columnas al español
- Guarda CSV y Excel con hoja de resumen por país

**Salidas:**
| Archivo | Tamaño |
|---|---|
| [revistas_sudamerica.csv](revistas_sudamerica.csv) | 3.0 MB |
| [revistas_sudamerica.xlsx](revistas_sudamerica.xlsx) | 1.2 MB |

**Resultados — Total: 2.780 revistas, 55 columnas**

| País | Revistas | % |
|---|---|---|
| Brasil | 1.415 | 50.9% |
| Colombia | 454 | 16.3% |
| Argentina | 407 | 14.6% |
| Chile | 194 | 7.0% |
| Perú | 149 | 5.4% |
| Ecuador | 105 | 3.8% |
| Uruguay | 31 | 1.1% |
| Paraguay | 25 | 0.9% |
| **TOTAL** | **2.780** | **100%** |

---

### Paso 2 — Clasificación temática y metodológica

**Script:** [analisis_tematico.py](analisis_tematico.py)
**Hora:** 10:25
**Entrada:** `revistas_sudamerica.csv`

**Lógica:**
- Asigna **macroárea** (11 categorías) según campo `areas_tematicas` (códigos LCC de DOAJ)
- Clasifica **metodología predominante** en 4 tipos según palabras clave de disciplina:
  - `Experimental`
  - `Inferencia Estadística`
  - `Experimental + Estadística`
  - `Cualitativa / Interpretativa`
- Genera flag booleano `usa_exp_o_estadistica`

**Salidas:**
| Archivo | Hojas | Tamaño |
|---|---|---|
| [revistas_clasificadas.csv](revistas_clasificadas.csv) | — | 3.2 MB |
| [revistas_clasificadas.xlsx](revistas_clasificadas.xlsx) | 4 (lista, macroárea, metodología, país+método) | 2.2 MB |

**Resultados — Clasificación por macroárea**

| Macroárea | N | % |
|---|---|---|
| Ciencias Naturales y Exactas | 1.197 | 43.1% |
| Ciencias Agrarias y Ambientales | 923 | 33.2% |
| Ciencias de la Salud | 313 | 11.3% |
| Educación | 116 | 4.2% |
| Psicología | 90 | 3.2% |
| Humanidades | 80 | 2.9% |
| Ingeniería y Tecnología | 34 | 1.2% |
| Derecho y Ciencias Jurídicas | 27 | 1.0% |
| Sin clasificar | — | — |

**Resultados — Clasificación por metodología**

| Metodología | N | % |
|---|---|---|
| Inferencia Estadística | 1.098 | 39.5% |
| Experimental + Estadística | 730 | 26.3% |
| Cualitativa / Interpretativa | 588 | 21.2% |
| Experimental | 209 | 7.5% |
| No determinado | 155 | 5.6% |

> **Revistas con inferencia estadística o experimental: 2.037 (73.3%)**

---

### Paso 3 — Diseño muestral estratificado

**Script:** [diseno_muestral.py](diseno_muestral.py)
**Hora:** 10:34
**Entrada:** `revistas_clasificadas.csv`

**Lógica:**
- Filtra solo revistas con metodología inferencial/experimental (excluye Derecho y Humanidades)
- Calcula tamaños muestrales para **dos métricas simultáneas**:
  - **M2** — % de revistas con ≥1 artículo con falla (nivel revista)
  - **M1** — % de artículos con falla dentro de cada revista (nivel artículo)
- Aplica corrección por población finita (FPC)
- Aplica efecto de diseño (DEFF) por correlación intraclase en 2da etapa
- Selección aleatoria estratificada proporcional (`random_state=42`)
- Genera instrumento de codificación con 7 tipos de fallas

**Parámetros del diseño:**

| Parámetro | Valor |
|---|---|
| Nivel de confianza | 95% (Z = 1.96) |
| Error M2 (nivel revista) | ±5 pp |
| Error M1 (nivel artículo) | ±8 pp |
| p esperada M2 | 0.50 (conservador) |
| p esperada M1 | 0.30 |
| ICC (correlación intraclase) | 0.10 |
| DEFF | 1 + (10−1)×0.10 = 1.90 |
| Artículos por revista (k) | 10 |
| Estratos excluidos | Derecho y Humanidades |

**Tamaños muestrales calculados:**

| Métrica | n sin FPC | n con FPC |
|---|---|---|
| M2 (nivel revista) | 384 | ~327 |
| M1 (revistas equivalentes) | calculado con DEFF | — |
| **Rector (max)** | — | **327 revistas** |

**Salidas:**
| Archivo | Hojas | Tamaño |
|---|---|---|
| [muestra_revistas.csv](muestra_revistas.csv) | — | 123 KB |
| [muestra_revistas.xlsx](muestra_revistas.xlsx) | 3 (muestra, diseño estratos, instrumento) | 59 KB |

**Resultados — Muestra final: 327 revistas / 3.270 artículos**

**Por macroárea:**

| Macroárea | Revistas | Artículos |
|---|---|---|
| Ciencias Naturales y Exactas | 146 | 1.460 |
| Ciencias Agrarias y Ambientales | 90 | 900 |
| Ciencias de la Salud | 51 | 510 |
| Educación | 19 | 190 |
| Psicología | 15 | 150 |
| Ingeniería y Tecnología | 6 | 60 |
| **TOTAL** | **327** | **3.270** |

**Por país:**

| País | Revistas | % |
|---|---|---|
| Brasil | 183 | 56.0% |
| Colombia | 47 | 14.4% |
| Argentina | 38 | 11.6% |
| Perú | 20 | 6.1% |
| Chile | 19 | 5.8% |
| Ecuador | 12 | 3.7% |
| Uruguay | 4 | 1.2% |
| Paraguay | 4 | 1.2% |

**Por metodología (muestra):**

| Metodología | Revistas |
|---|---|
| Inferencia Estadística | 165 |
| Experimental + Estadística | 126 |
| Experimental | 36 |

**Protocolo de codificación — 7 tipos de fallas a detectar por artículo:**

| # | Falla |
|---|---|
| 1 | Uso de prueba paramétrica sin verificar normalidad |
| 2 | Comparaciones múltiples sin corrección (Bonferroni, FDR, etc.) |
| 3 | p-valor sin reporte de tamaño de efecto |
| 4 | Confusión entre significancia estadística y práctica |
| 5 | Muestra insuficiente / sin cálculo de potencia |
| 6 | Variables ordinales tratadas como de razón |
| 7 | Extrapolación fuera del ámbito del diseño muestral |

---

### Resumen del pipeline — Sesión 2026-03-28

```
DOAJ (21.000 revistas globales)
        ↓  filter_sudamerica()
   2.780 revistas sudamericanas  [revistas_sudamerica.csv]
        ↓  clasificar_metodologia() + asignar_macroarea()
   2.037 revistas inferenciales/experimentales (73.3%)  [revistas_clasificadas.csv]
        ↓  diseño MEP + FPC + DEFF  (excluye Derecho y Humanidades)
     327 revistas seleccionadas → 3.270 artículos a revisar  [muestra_revistas.csv]
```

### Estado al cierre de la sesión

| Item | Estado |
|---|---|
| Pipeline de descarga y clasificación | ✅ Completo |
| Diseño muestral calculado | ✅ Completo |
| Muestra aleatoria generada | ✅ Completa (seed=42) |
| Auditoría de artículos | ⏳ Pendiente |
| Análisis de fallas por macroárea | ⏳ Pendiente |

### Próximos pasos sugeridos
1. Revisar la distribución de la muestra en `muestra_revistas.xlsx` → hoja `Diseño_estratos`
2. Iniciar auditoría usando el instrumento en hoja `Instrumento_codificacion`
3. Completar las 7 fallas por artículo y consolidar resultados
4. Calcular prevalencias con estimador de Horvitz-Thompson o Taylor

---

---

### Paso 4 — Obtención de artículos y URLs desde DOAJ

**Script:** [fetch_articulos_muestra.py](fetch_articulos_muestra.py)
**Hora:** 13:09
**Entrada:** `muestra_revistas.csv` (327 revistas)

**Lógica:**
- Consulta la API pública de DOAJ por ISSN de cada revista (`https://doaj.org/api/search/articles/issn:{issn}?pageSize=100`)
- Descarga hasta 100 artículos por revista
- Selecciona los 10 más recientes (priorizando años ≥ 2018)
- Extrae: título, año, autores, URL fulltext, DOI, abstract, palabras clave
- Genera log de estado por revista

**Salidas:**
| Archivo | Descripción | Estado |
|---|---|---|
| [base_articulos_muestra.csv](base_articulos_muestra.csv) | Base principal de artículos con URLs | ✅ Guardado |
| [fetch_articulos_log.csv](fetch_articulos_log.csv) | Estado por revista (total DOAJ, seleccionados) | ✅ Guardado |
| `base_articulos_muestra.xlsx` | Excel (3 hojas) | ⚠️ Error por caracteres especiales en título |

**Resultados:**

| Métrica | Valor |
|---|---|
| Revistas procesadas | 327 |
| Revistas con error de red | 0 |
| **Total artículos obtenidos** | **2.675** |
| Con URL fulltext | 2.658 (99.4%) |
| Con DOI | 2.143 (80.1%) |
| Rango de años | 2003 – 2026 |

**Por macroárea:**

| Macroárea | Artículos | Con URL |
|---|---|---|
| Ciencias Naturales y Exactas | 1.221 | 1.211 (99.2%) |
| Ciencias Agrarias y Ambientales | 744 | 744 (100%) |
| Ciencias de la Salud | 400 | 399 (99.8%) |
| Educación | 130 | 124 (95.4%) |
| Psicología | 130 | 130 (100%) |
| Ingeniería y Tecnología | 50 | 50 (100%) |
| **TOTAL** | **2.675** | **2.658 (99.4%)** |

**Hallazgo importante:** No todas las revistas en DOAJ tienen artículos indexados.
De 327 revistas: ~245 tuvieron artículos (10 c/u) y ~82 devolvieron 0 artículos desde la API.
Estas últimas están en el log como `SIN_ARTICULOS` y podrían consultarse directamente por URL.

**Campos en `base_articulos_muestra.csv`:**
`nro`, `id_revista`, `macroarea`, `metodologia`, `pais`, `revista`, `issn`, `titulo`, `anio`, `autores`, `url_fulltext`, `doi`, `abstract`, `palabras_clave`

**Pendiente:**
- Corregir generación del Excel (caracteres especiales en títulos)
- Script de descarga de PDFs desde `url_fulltext` (fase siguiente)

---

### Resumen del pipeline completo — Sesión 2026-03-28

```
DOAJ journal CSV (21.000 revistas globales)
        ↓  fetch_journals_sudamerica.py
   2.780 revistas sudamericanas  [revistas_sudamerica.csv]
        ↓  analisis_tematico.py
   2.037 revistas inferenciales/experimentales (73.3%)  [revistas_clasificadas.csv]
        ↓  diseno_muestral.py  (MEP + FPC + DEFF, excluye Derecho y Humanidades)
     327 revistas seleccionadas  [muestra_revistas.csv]
        ↓  fetch_articulos_muestra.py  (API DOAJ por ISSN)
   2.675 artículos con URL fulltext (99.4%)  [base_articulos_muestra.csv]
        ↓  (pendiente)
   Descarga de PDFs
```

### Estado al cierre de la sesión

| Item | Estado |
|---|---|
| Pipeline de descarga y clasificación de revistas | ✅ Completo |
| Diseño muestral calculado | ✅ Completo |
| Muestra aleatoria generada (seed=42) | ✅ Completo |
| Base de artículos con URLs | ✅ Completo (2.675 artículos) |
| Corrección Excel `base_articulos_muestra.xlsx` | ⏳ Pendiente |
| Descarga de PDFs | ⏳ Pendiente |
| Auditoría de fallas metodológicas | ⏳ Pendiente |

### Paso 5 — Script de análisis metodológico con Claude API

**Script:** [analizar_pdf_articulos.py](analizar_pdf_articulos.py)
**Modelo:** `claude-opus-4-6` con adaptive thinking
**Entrada:** Carpeta `pdfs_articulos/` (PDFs descargados)

**Lógica:**
- Lee cada PDF con `pdfplumber` (trunca a 14.000 chars si es muy largo)
- Envía texto a Claude API con salida estructurada Pydantic (`client.messages.parse`)
- Guarda progreso incremental cada 10 artículos (reanudable)
- Maneja rate limits automáticamente (pausa 60s y reintenta)

**20 campos extraídos por artículo:**

| Grupo | Campos |
|---|---|
| Metadatos (de base_articulos_muestra) | id_revista, revista, pais, macroarea, titulo, anio, autores, doi, url_fulltext |
| Clasificación | disciplina, tipo_estudio, enfoque_metodologico, diseno_estudio |
| Contexto | objetivo_general, frase_inferencia, frase_muestreo, tamano_muestra |
| Variables binarias (Sí/No) | es_cuantitativo_con_inferencia, muestreo_probabilistico, muestreo_no_probabilistico, declara_tipo_muestreo, declara_calculo_tamano_muestral, reporta_intervalos_confianza, extrapola_a_poblacion, advierte_limites_muestreo |
| **Variable resultado** | **incumple_inferencia** (Sí / No / No aplica) |
| Complementarios | software_estadistico, conclusion_falla |

**Criterio para `incumple_inferencia = 'Sí'`:**
> Artículo usa estadística inferencial O extrapola resultados, Y la muestra es NO probabilística, Y NO advierte esta limitación.

**Salidas:**
| Archivo | Descripción |
|---|---|
| `base_auditoria.csv` | Base principal — una fila por artículo |
| `base_auditoria.xlsx` | Ídem + hojas: Resumen_resultado, Resumen_macroarea, Log |
| `auditoria_log.csv` | Estado por PDF (OK / SIN_TEXTO / ERROR) |

**Uso:**
```bash
python analizar_pdf_articulos.py
python analizar_pdf_articulos.py --carpeta "ruta/alternativa/pdfs"
python analizar_pdf_articulos.py --reiniciar   # reprocesa todo
```

**Estado:** ⏳ Pendiente — requiere PDFs descargados en `pdfs_articulos/`

---

---

### Paso 6 — Descarga de PDFs

**Script:** [descargar_pdfs_articulos.py](descargar_pdfs_articulos.py)
**Hora inicio:** 13:32
**Entrada:** `base_articulos_muestra.csv` (2.658 artículos con URL)

**Lógica — 4 estrategias según patrón de URL:**

| Estrategia | Patrón de URL | Método |
|---|---|---|
| `ojs_citation_pdf_url` | `/article/view/{id}` | Lee HTML → extrae `<meta name="citation_pdf_url">` |
| `ojs_download` | `/article/view/{id}` | Prueba rutas `/article/download/{id}/pdf`, `/1` |
| `html_parse` | Redalyc, otros | Lee HTML → extrae `<meta name="citation_pdf_url">` |
| `scielo_*` | `sci_arttext` | Reemplaza por `sci_pdf`, o parsea HTML |

**Características técnicas:**
- Deshabilita verificación SSL globalmente vía `HTTPAdapter` (necesario para servidores latinoamericanos con certificados self-signed)
- Delay de 1.2s entre descargas, 3.0s adicional tras errores
- Resume automáticamente: omite artículos ya descargados (`estado == "OK"` en log)
- Guarda log incremental cada 20 artículos
- Nombre de archivo: `{nro:05d}_{revista}_{anio}.pdf`

**Plataformas dominantes en la base:**

| Dominio | Artículos | % |
|---|---|---|
| scielo.br | 382 | 14.3% |
| revistas.usp.br | 63 | 2.4% |
| revistas.udistrital.edu.co | 50 | 1.9% |
| redalyc.org | 50 | 1.9% |
| otros (>200 dominios) | ~2.100 | ~79% |

**Correcciones aplicadas durante prueba piloto:**
1. **`citation_pdf_url` no reconocida:** la función `extraer_pdf_desde_html` solo buscaba metas con content que termina en `.pdf`, pero OJS genera URLs como `/article/download/210/171` sin extensión. → Se agregó como **prioridad 0** la búsqueda de `<meta name="citation_pdf_url">`.
2. **SSL fallos en servidores latinoamericanos:** `SESSION.verify = False` no funciona en la versión de requests instalada. → Se implementó `_NoSSLAdapter` (subclase de `HTTPAdapter`) que fuerza `verify=False` a nivel de adaptador.
3. **OpenEdition (journals.openedition.org):** 10 artículos (0.4%) están detrás de Anubis bot-protection — no accesibles con scraping estándar. Pérdida asumida.

**Prueba piloto (primeros 40 artículos):**

| Artículos | Exitosos | Estrategia |
|---|---|---|
| 10 (Redalyc) | 10/10 | `html_parse` (via citation_pdf_url) |
| 10 (OJS — Cartografías del Sur) | 10/10 | `ojs_citation_pdf_url` |
| 10 (OJS — Clio y Asociados) | 10/10 | `ojs_citation_pdf_url` |
| 10 (OpenEdition) | 0/10 | — (bot protection) |

**Estado:** 🔄 Descarga completa en curso (~2.628 artículos restantes, ~53 min)

**Salidas:**
| Archivo | Descripción |
|---|---|
| `pdfs_articulos/` | Carpeta con PDFs descargados |
| [descarga_pdfs_log.csv](descarga_pdfs_log.csv) | Log por artículo: estrategia, tamaño, estado |

**Uso:**
```bash
python descargar_pdfs_articulos.py              # descarga completa
python descargar_pdfs_articulos.py --limite 50  # prueba con 50
python descargar_pdfs_articulos.py --reiniciar  # reprocesa errores
```

---

### Resumen del pipeline completo — Sesión 2026-03-28

```
DOAJ journal CSV (21.000 revistas globales)
        ↓  fetch_journals_sudamerica.py
   2.780 revistas sudamericanas  [revistas_sudamerica.csv]
        ↓  analisis_tematico.py
   2.037 revistas inferenciales/experimentales (73.3%)  [revistas_clasificadas.csv]
        ↓  diseno_muestral.py  (MEP + FPC + DEFF, excluye Derecho y Humanidades)
     327 revistas seleccionadas  [muestra_revistas.csv]
        ↓  fetch_articulos_muestra.py  (API DOAJ por ISSN)
   2.675 artículos con URL fulltext (99.4%)  [base_articulos_muestra.csv]
        ↓  descargar_pdfs_articulos.py  (4 estrategias + SSL bypass)
   PDFs en pdfs_articulos/  [descarga_pdfs_log.csv]
        ↓  analizar_pdf_articulos.py  (Claude claude-opus-4-6 + Pydantic)
   base_auditoria.csv  ← RESULTADO FINAL
```

### Estado al cierre de la sesión

| Item | Estado |
|---|---|
| Pipeline de descarga y clasificación de revistas | ✅ Completo |
| Diseño muestral calculado | ✅ Completo |
| Muestra aleatoria generada (seed=42) | ✅ Completo |
| Base de artículos con URLs (2.675 art.) | ✅ Completo |
| Script descarga PDFs | ✅ Completo y validado |
| Descarga completa de PDFs | 🔄 En curso |
| Script análisis metodológico con Claude API | ✅ Listo para ejecutar |
| Auditoría de fallas metodológicas | ⏳ Pendiente |

### Próximos pasos
1. Verificar resultados de la descarga completa (`descarga_pdfs_log.csv`)
2. Ejecutar `analizar_pdf_articulos.py` sobre los PDFs descargados
3. Revisar revistas sin artículos en DOAJ (`SIN_ARTICULOS`) — evaluar fuente alternativa
4. Calcular prevalencias con estimador de Horvitz-Thompson

---

---

### Paso 7 — Análisis metodológico paralelo con Gemini 2.5 Flash

**Scripts:** [analizar_pdf_articulos.py](analizar_pdf_articulos.py)
**Modelo:** `gemini-2.5-flash` (Google AI Studio)
**Hora:** 16:34 – 20:15 (2026-03-28/29)
**6 agentes paralelos** (_p1 a _p6), ~373 artículos cada uno

**Resultado merge:** [base_auditoria_FINAL.csv](base_auditoria_FINAL.csv) — 2.191 artículos

---

### RESULTADOS DEFINITIVOS

**n = 2.191 artículos | 148 revistas | 8 países | 6 macroáreas**

#### Prevalencias principales

| Métrica | % | IC 95% |
|---|---|---|
| **M1b** — Falla entre artículos con inferencia | **79.8%** | [76.2% – 82.9%] |
| **M1** — Falla en todos los artículos | **20.5%** | [18.9% – 22.2%] |
| **M2** — Revistas con ≥1 artículo con falla | **92.6%** | [87.2% – 95.8%] |

#### Por macroárea (solo artículos con inferencia)

| Macroárea | n | Falla | IC 95% |
|---|---|---|---|
| Ciencias Agrarias y Ambientales | 154 | 90.9% | [85.3–94.5] |
| Ingeniería y Tecnología | 9 | 88.9% | [56.5–98.0] |
| Educación | 7 | 85.7% | [48.7–97.4] |
| Ciencias Naturales y Exactas | 195 | 77.9% | [71.6–83.2] |
| Psicología | 27 | 77.8% | [59.2–89.4] |
| Ciencias de la Salud | 170 | 71.8% | [64.6–78.0] |

#### Por país (solo artículos con inferencia)

| País | n | Falla | IC 95% |
|---|---|---|---|
| Uruguay | 14 | 100.0% | [78.5–100.0] |
| Chile | 14 | 85.7% | [60.1–96.0] |
| Argentina | 39 | 82.1% | [67.3–91.0] |
| Colombia | 65 | 81.5% | [70.4–89.1] |
| Brasil | 352 | 81.0% | [76.5–84.7] |
| Ecuador | 21 | 71.4% | [50.0–86.2] |
| Perú | 50 | 66.0% | [52.2–77.6] |
| Paraguay | 7 | 71.4% | [35.9–91.8] |

#### Variables secundarias (artículos con inferencia, n=563)

| Variable | % | IC 95% |
|---|---|---|
| Muestra no probabilística | 90.9% | [88.3–93.0] |
| Extrapola a población | 86.7% | [83.6–89.2] |
| NO advierte límites de muestreo | 85.6% | [82.5–88.3] |
| NO justifica tamaño muestral | 84.5% | [81.3–87.3] |
| NO reporta intervalos de confianza | 82.1% | [78.7–85.0] |
| NO declara tipo de muestreo | 56.7% | [52.5–60.7] |

#### Tendencia temporal — sin mejora
Años 2003–2026: falla sostenida 72–100% sin tendencia decreciente significativa.

---

### Estado final de la sesión

| Item | Estado |
|---|---|
| Pipeline completo (pasos 1–6) | ✅ Completo |
| Análisis Gemini 2.5 Flash (6 agentes) | ✅ Completo |
| Merge base_auditoria_FINAL.csv | ✅ 2.191 artículos |
| Prevalencias con IC 95% | ✅ Calculadas |
| Excel final con hojas de resumen | ⏳ Pendiente |
| Estimación Horvitz-Thompson por estrato | ⏳ Pendiente |

---

*Ultima actualizacion de esa fase: 2026-03-29 00:15*

---

## Addendum maestro - Replanteamiento, ampliacion del universo y estado consolidado

**Periodo:** `2026-03-30` a `2026-04-01`

### 1. Aclaracion historica importante

El bloque anterior de la bitacora resume correctamente el **primer gran cierre operativo** del proyecto, pero ya no representa por si solo el estado metodologico vigente.

Entre `2026-03-30` y `2026-04-01` ocurrieron cuatro cambios mayores:

1. se replanteo la variable principal, pasando del esquema binario historico `incumple_inferencia = Si / No / No aplica` a una clasificacion inferencial mas informativa;
2. se separo la **elegibilidad del universo** de la **auditoria de fallas**;
3. se integro un lote grande adicional de PDFs desde `PDFs/`;
4. se construyo una base ampliada del universo cuantitativo con inferencia, con imputacion de macroarea y tablas finales por area.

Por eso, los resultados del cierre del `2026-03-29` deben leerse como **antecedente operativo relevante**, pero no como el ultimo punto conceptual del proyecto.

### 2. Replanteamiento metodologico

Se decidio no pedir mas a Gemini que juzgue directamente la falla metodologica sobre todo el universo mezclado. En cambio, la logica nueva quedo definida asi:

1. integrar todos los PDFs disponibles en una sola base;
2. decidir primero si cada unidad es o no un **estudio cuantitativo que aplica inferencia**;
3. solo despues auditar fallas inferenciales dentro de ese subconjunto.

Este replanteamiento quedo formalizado en:

- `REPLANTEAMIENTO_V4_VARIABLE_PRINCIPAL_2026-03-30.md`
- `REAPERTURA_CRITERIO_AMPLIO_2026-03-30.md`
- `REPORTE_AJUSTES_V4_1_2026-03-30.md`

La nueva variable principal de auditoria paso a ser:

- `clasificacion_inferencial = Falla fuerte | Debilidad importante | Sin falla relevante | No aplica`

Y la compatibilidad con la variable historica quedo asi:

- `Falla fuerte` -> `incumple_inferencia = Si`
- `Debilidad importante` -> `incumple_inferencia = No`
- `Sin falla relevante` -> `incumple_inferencia = No`
- `No aplica` -> `incumple_inferencia = No aplica`

### 3. Calibracion v4 y v4.1

Se realizo una recalibracion del prompt de auditoria:

- `v4` separo mejor el universo aplicable de los `No aplica`, pero seguia funcionando casi de forma binaria;
- la categoria `Debilidad importante` quedo vacia o practicamente vacia;
- por eso se ajusto el prompt a `v4.1`, reservando `Falla fuerte` para quiebres inferenciales realmente sustantivos y empujando los casos frontera hacia `Debilidad importante`.

Resultado clave del piloto `v4.1`:

| Clase | n |
|---|---:|
| `No aplica` | `29` |
| `Falla fuerte` | `3` |
| `Debilidad importante` | `3` |
| `Sin falla relevante` | `1` |

Lectura:

- `v4.1` corrigio el sesgo binario de `v4`;
- la clase `Debilidad importante` aparecio de forma plausible;
- el ajuste fue aceptado conceptualmente.

Ademas:

- se mejoro `analizar_pdf_articulos.py` para manejar `429 RESOURCE_EXHAUSTED`;
- se agregaron `--reintentos-429`, `--espera-429` y `--cortar-en-cuota`;
- se creo `generar_reporte_calibracion_v4_1.py` para cerrar automaticamente reportes de calibracion.

La corrida media `v4.1` quedo frenada por cuota externa de Gemini, no por fallo del codigo.

### 4. Integracion del universo ampliado de PDFs

Antes de continuar con la auditoria de fallas, se integro un nuevo lote de PDFs para reconstruir el universo real de interes.

**Fuentes integradas:**

- `pdfs_articulos/`
- `PDFs/`

**Script principal:**

- `integrar_pdfs_universo_inferencia.py`

**Resultado de integracion:**

| Indicador | n |
|---|---:|
| PDFs en `pdfs_articulos` | `2196` |
| PDFs adicionales en `PDFs` | `507` |
| Total de PDFs fisicos | `2703` |
| Unidades analiticas | `2721` |
| Con screening previo reutilizable | `2209` |
| Pendientes del primer filtro con Gemini | `493` |
| PDFs-lote multiarticulo | `19` |
| Articulos legacy en `.txt` dentro de lotes | `18` |

**Artefactos principales:**

- `inventario_pdfs_fuentes.csv`
- `universo_analitico_inferencia.csv`
- `resumen_integracion_pdfs.json`

### 5. Nuevo screening: cuantitativo con inferencia

Se creo un screening ligero y separado de la auditoria de fallas:

- `screening_cuant_inferencia_gemini.py`

Este script solo decide:

- `es_cuantitativo_con_inferencia = Si / No`

No juzga todavia falla metodologica.

**Piloto inicial:**

- `20` casos procesados
- `7` clasificados como `Si`
- `13` clasificados como `No`

**Cierre operativo del screening del universo ampliado:**

| Resultado | n |
|---|---:|
| Universo final `Si` | `774` |
| Universo final `No` | `1912` |
| PDFs problematicos de lectura | `16` |
| Pendientes reales despues de reconciliar el log | `0` |

**Composicion del universo final `Si`:**

| Origen | n |
|---|---:|
| Desde `base_auditoria_FINAL` | `563` |
| Desde screening nuevo con Gemini | `203` |
| Desde `.txt` legacy | `8` |

**Reportes asociados:**

- `REPORTE_CIERRE_UNIVERSO_CUANT_INFERENCIA_2026-03-31.md`
- `REPORTE_DETALLADO_LOGROS_Y_PENDIENTES_2026-03-31.md`

### 6. Asignacion de macroarea faltante

Una vez cerrado el universo `Si`, se detecto que `211` articulos no tenian macroarea consolidada.

Se creo:

- `clasificar_macroarea_faltante_gemini.py`

**Resultado de la deduccion de macroarea:**

| Indicador | n |
|---|---:|
| Casos sin macroarea inicial | `211` |
| Casos resueltos por Gemini | `205` |
| Casos todavia sin asignacion final | `6` |

Los `6` restantes no quedaron sin resolver por duda tematica, sino por errores de red en esa corrida.

Despues, por decision operativa, esos `6` casos conflictivos se excluyeron del analisis.

### 7. Universo real de analisis despues de excluir 6 conflictivos

Tras excluir esos `6` casos, el universo de interes quedo en:

- **`768` articulos cuantitativos con inferencia**

Este universo final esta guardado en:

- `lista_final_universo_si_sin_6_conflictivos.csv`

**Distribucion final por area tematica del universo de interes (`n = 768`):**

| Area | n | % |
|---|---:|---:|
| Ciencias de la Salud | `234` | `30.5` |
| Ciencias Naturales y Exactas | `206` | `26.8` |
| Ciencias Agrarias y Ambientales | `187` | `24.3` |
| Ingenieria y Tecnologia | `61` | `7.9` |
| Psicologia | `54` | `7.0` |
| Educacion | `26` | `3.4` |

### 8. Que significa `No aplica`

En el esquema nuevo, `No aplica` **no significa** "articulo correcto" ni "articulo sin problemas".

Significa:

- la auditoria de muestreo inferencial **no corresponde** a ese tipo de articulo.

Ejemplos tipicos de `No aplica`:

- meta-analisis;
- revisiones sistematicas;
- series de tiempo macroeconomicas exhaustivas;
- paneles censales de estados, municipios o instituciones;
- experimentos de laboratorio, `in vitro`, `ex vivo` o con animales;
- estudios ecologicos con registros completos;
- trabajos teoricos o metodologicos sin problema muestral clasico.

Por eso conviene distinguir siempre entre:

- **universo de interes**: articulos cuantitativos con inferencia (`768`);
- **poblacion analitica real para juzgar falla inferencial**: articulos a los que el criterio realmente aplica.

### 9. Base observada con clasificacion inferencial y poblacion analitica real

Para las tablas finales por area se uso:

- `base_auditoria_universo_772_final.csv`

Luego se reconcilio esa base con:

- `lista_final_universo_si_sin_6_conflictivos.csv`

Resultado de la reconciliacion:

- `766` articulos quedaron con clasificacion y area asignada;
- `6` registros de la auditoria `772 final` no emparejaron con la lista final sin conflictivos;
- `2` articulos del universo final no quedaron reflejados en esta base observada.

Dentro de esos `766` articulos observados:

| Clase | n |
|---|---:|
| `No aplica` | `343` |
| `Falla fuerte` | `298` |
| `Debilidad importante` | `104` |
| `Sin falla relevante` | `21` |

Entonces, la **poblacion analitica real** para estudiar falla inferencial con el criterio actual es:

- **`423` articulos aplicables**

porque:

- `298 + 104 + 21 = 423`

### 10. Distribucion por area de los 423 articulos aplicables

| Area | n aplicables | % |
|---|---:|---:|
| Ciencias de la Salud | `166` | `39.2` |
| Ciencias Naturales y Exactas | `87` | `20.6` |
| Ciencias Agrarias y Ambientales | `77` | `18.2` |
| Psicologia | `49` | `11.6` |
| Ingenieria y Tecnologia | `23` | `5.4` |
| Educacion | `21` | `5.0` |

### 11. Tablas finales por area con criterio amplio

Se definio:

- `falla amplia = Falla fuerte + Debilidad importante`

Archivos generados:

- `tabla_clasificacion_inferencial_por_area_2026-04-01.csv`
- `tabla_falla_amplia_por_area_total_2026-04-01.csv`
- `tabla_falla_amplia_por_area_aplicables_2026-04-01.csv`
- `REPORTE_TABLAS_CRITERIO_AMPLIO_POR_AREA_2026-04-01.md`

#### 11.1. Falla amplia sobre el total observado de cada area (`n = 766`)

| Area | n total auditado | n falla amplia | % falla amplia sobre total |
|---|---:|---:|---:|
| Ciencias de la Salud | `234` | `162` | `69.2` |
| Ciencias Naturales y Exactas | `206` | `81` | `39.3` |
| Ciencias Agrarias y Ambientales | `187` | `75` | `40.1` |
| Ingenieria y Tecnologia | `61` | `21` | `34.4` |
| Psicologia | `52` | `44` | `84.6` |
| Educacion | `26` | `19` | `73.1` |
| **Total** | **`766`** | **`402`** | **`52.5`** |

#### 11.2. Falla amplia solo entre articulos aplicables (`n = 423`)

| Area | Fallas amplias / aplicables | % |
|---|---:|---:|
| Ciencias de la Salud | `162 / 166` | `97.6` |
| Ciencias Naturales y Exactas | `81 / 87` | `93.1` |
| Ciencias Agrarias y Ambientales | `75 / 77` | `97.4` |
| Psicologia | `44 / 49` | `89.8` |
| Ingenieria y Tecnologia | `21 / 23` | `91.3` |
| Educacion | `19 / 21` | `90.5` |
| **Total** | **`402 / 423`** | **`95.0`** |

#### 11.3. Version mas estricta: solo `Falla fuerte`

Si se usa una definicion mas estricta de falla y se cuenta solo `Falla fuerte`, entonces:

- total global = `298 / 423 = 70.4%`

Por area:

| Area | Falla fuerte / aplicables | % |
|---|---:|---:|
| Ciencias de la Salud | `109 / 166` | `65.7` |
| Ciencias Naturales y Exactas | `58 / 87` | `66.7` |
| Ciencias Agrarias y Ambientales | `60 / 77` | `77.9` |
| Psicologia | `35 / 49` | `71.4` |
| Ingenieria y Tecnologia | `21 / 23` | `91.3` |
| Educacion | `15 / 21` | `71.4` |
| **Total** | **`298 / 423`** | **`70.4`** |

### 12. Areas subrepresentadas y necesidad de expansion muestral

Tomando como referencia la mayor muestra aplicable actual:

- Ciencias de la Salud = `166`

faltan estos articulos **aplicables** para igualar ese maximo:

| Area | Aplicables actuales | Faltan para llegar a 166 |
|---|---:|---:|
| Ciencias Naturales y Exactas | `87` | `79` |
| Ciencias Agrarias y Ambientales | `77` | `89` |
| Psicologia | `49` | `117` |
| Ingenieria y Tecnologia | `23` | `143` |
| Educacion | `21` | `145` |

Total faltante en terminos de articulos aplicables:

- **`573` articulos**

Si se proyecta la misma tasa observada de aplicabilidad por area, la necesidad bruta de descarga adicional seria aproximadamente:

| Area | Descargas brutas estimadas |
|---|---:|
| Ciencias Naturales y Exactas | `188` |
| Ciencias Agrarias y Ambientales | `217` |
| Psicologia | `125` |
| Ingenieria y Tecnologia | `380` |
| Educacion | `180` |
| **Total estimado** | **`1090`** |

### 13. Estado actual consolidado

**Lo ya logrado:**

- pipeline original completo;
- replanteamiento conceptual del criterio de auditoria;
- integracion del universo ampliado de PDFs;
- screening separado de elegibilidad cuantitativa con inferencia;
- cierre operativo del universo `Si`;
- imputacion de macroarea casi completa;
- definicion del universo de interes (`768`);
- definicion de la poblacion analitica real (`423`);
- tablas finales por area con criterio amplio y con criterio estricto.

**Lo pendiente:**

- decidir cual denominador usara el manuscrito en cada seccion (`768`, `766` o `423`);
- recuperar o revisar los `16` PDFs problematicos de lectura;
- decidir si conviene expandir muestra en areas subrepresentadas;
- eventualmente retomar calibracion `v4.1` media cuando haya cuota suficiente, si se desea completar esa linea metodologica como evidencia adicional.

### 14. Archivos clave al cierre de esta fase

- `base_auditoria_FINAL.csv`
- `integrar_pdfs_universo_inferencia.py`
- `screening_cuant_inferencia_gemini.py`
- `universo_analitico_inferencia_reconciliado.csv`
- `lista_final_universo_si_cuant_inferencia.csv`
- `lista_final_universo_si_sin_6_conflictivos.csv`
- `macroarea_deducida_211_gemini.csv`
- `lista_final_universo_si_cuant_inferencia_con_macroarea.csv`
- `tabla_clasificacion_inferencial_por_area_2026-04-01.csv`
- `tabla_falla_amplia_por_area_total_2026-04-01.csv`
- `tabla_falla_amplia_por_area_aplicables_2026-04-01.csv`
- `REPORTE_CIERRE_UNIVERSO_CUANT_INFERENCIA_2026-03-31.md`
- `REPORTE_DETALLADO_LOGROS_Y_PENDIENTES_2026-03-31.md`
- `REPORTE_AVANCE_DEDUCCION_MACROAREA_NORMALIZADO_2026-04-01.md`
- `REPORTE_TABLAS_CRITERIO_AMPLIO_POR_AREA_2026-04-01.md`

---

### 15. Actualizacion oficial de metricas (consolidado + expansion)

Esta tabla reemplaza el consolidado previo con `SIN_AREA = 199`.
Se reconstruyo usando:

- base historica auditada (`n = 772`);
- imputacion de area por `macroarea_final` desde `lista_final_universo_si_cuant_inferencia_con_macroarea.csv`;
- lote expansion `r4` (`93` PDFs, `92` analizados OK, `1` SIN_TEXTO).

**Resultado consolidado actualizado (`n analizados = 864`)**

| Area | Total analizados | Poblacion real aplicable | Falla fuerte (n) | Falla relajada (n) | % Falla fuerte (aplicables) | % Falla relajada (aplicables) |
|---|---:|---:|---:|---:|---:|---:|
| Ciencias de la Salud | `227` | `159` | `102` | `155` | `64.2` | `97.5` |
| Ciencias Naturales y Exactas | `206` | `87` | `58` | `81` | `66.7` | `93.1` |
| Ciencias Agrarias y Ambientales | `188` | `78` | `61` | `76` | `78.2` | `97.4` |
| Ingenieria y Tecnologia | `88` | `35` | `32` | `33` | `91.4` | `94.3` |
| Psicologia | `73` | `66` | `48` | `61` | `72.7` | `92.4` |
| Educacion | `46` | `26` | `18` | `24` | `69.2` | `92.3` |
| Ciencias sociales y humanidades | `30` | `16` | `11` | `16` | `68.8` | `100.0` |
| SIN_AREA | `6` | `3` | `2` | `2` | `66.7` | `66.7` |
| **TOTAL** | **`864`** | **`470`** | **`332`** | **`448`** | **`70.6`** | **`95.3`** |

**Archivo fuente oficial de esta tabla:**

- `tabla_metricas_totales_por_area_consolidado_macroarea_final_2026-04-01.csv`

---

*Ultima actualizacion general: 2026-04-01*
