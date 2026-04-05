# Errores Inferenciales Críticos en Estudios Cuantitativos Sudamericanos

> **Paquete de replicación para el artículo sometido a la revista *DADOS — Revista de Ciências Sociais*.**

## Resumen del estudio

Este repositorio contiene los datos, scripts de análisis y código fuente del manuscrito:

> **Errores inferenciales críticos en estudios cuantitativos publicados en revistas sudamericanas de acceso abierto**
>
> Diego Bernardo Meza Bogado — FACEN-UNA

El estudio estima la prevalencia de fallas inferenciales críticas en 628 artículos cuantitativos publicados en revistas sudamericanas de acceso abierto (DOAJ), y cuantifica mediante simulación Monte Carlo el impacto de aplicar estadística inferencial sobre muestras no probabilísticas.

## Estructura del repositorio

```
├── datos/                               # Bases de datos y documentación del proceso
│   ├── BASE_FINAL_ANALISIS_2026-04-03.csv   # ★ Base analítica final (628 artículos)
│   ├── base_articulos_muestra.csv           # Muestra amplia de artículos recolectados
│   ├── muestra_revistas.csv                 # Revistas seleccionadas por muestreo
│   ├── revistas_sudamerica.csv              # Universo de revistas DOAJ sudamericanas
│   ├── BITACORA.md                          # Bitácora detallada del proceso
│   ├── ESQUEMA_PIPELINE.md                  # Esquema del pipeline de procesamiento
│   └── ESQUEMA_PIPELINE.png                 # Diagrama visual del pipeline
│
├── scripts/                             # Código fuente para replicación
│   ├── 01_recoleccion/                  # Fase I: Descubrimiento y descarga
│   │   ├── fetch_journals_sudamerica.py     # Obtención del universo DOAJ
│   │   ├── fetch_articulos_muestra.py       # Consulta API DOAJ para artículos
│   │   ├── descargar_pdfs_articulos.py      # Descarga masiva de PDFs
│   │   ├── download_urls.py                 # Utilidad de descarga
│   │   ├── expandir_descargar_areas_objetivo.py  # Expansión por áreas
│   │   └── diseno_muestral.py               # Cálculos de diseño muestral
│   │
│   ├── 02_extraccion_ia/               # Fase II: Auditoría con IA (Gemini)
│   │   ├── extract_with_gemini.py           # Extracción JSON con Gemini
│   │   ├── analizar_pdf_articulos.py        # Análisis masivo de PDFs
│   │   ├── screening_cuant_inferencia_gemini.py  # Screening cuant/inferencial
│   │   ├── clasificar_macroarea_faltante_gemini.py  # Clasificación de macroáreas
│   │   ├── integrar_pdfs_universo_inferencia.py     # Integración del universo
│   │   └── PROMPT_V4_BORRADOR.txt           # Prompt utilizado para Gemini
│   │
│   ├── 03_simulacion/                   # Fase III: Simulación Monte Carlo
│   │   ├── calculos_tablas_figuras.py       # ★ Cálculos, tablas y simulación MC
│   │   └── fig_simulacion_resultados.py     # Generación de figuras de simulación
│   │
│   ├── 04_figuras_tablas/               # Generación de figuras del artículo
│   │   ├── generar_reporte_figuras.py       # Figuras de resultados empíricos
│   │   └── generar_diagrama_metodologia.py  # Diagrama de flujo metodológico
│   │
│   └── utilidades/                      # Utilidades compartidas
│       ├── config.py                        # Configuración de rutas
│       ├── compare_classifications.py       # Comparación de clasificaciones
│       └── validacion_app.py                # App Streamlit de validación humana
│
└── manuscrito/                          # Código fuente LaTeX (formato DADOS)
    ├── main.tex                             # Archivo principal
    ├── introduccion.tex ... consideraciones.tex  # Secciones modulares
    ├── apendices.tex                        # Apéndices A, B y C
    ├── referencias_dados.tex                # Bibliografía
    └── tablasyfig/                          # Figuras y tablas
```

## Requisitos

### Para los scripts de análisis
```bash
pip install pandas pdfplumber google-generativeai pydantic matplotlib seaborn scipy
```

### Para el manuscrito LaTeX
Cualquier distribución TeX moderna (TeX Live, MiKTeX, tectonic).

## Cómo replicar

### 1. Recolección de datos (Fase I)
```bash
# Obtener universo de revistas DOAJ sudamericanas
python scripts/01_recoleccion/fetch_journals_sudamerica.py

# Obtener artículos por revista
python scripts/01_recoleccion/fetch_articulos_muestra.py

# Descargar PDFs
python scripts/01_recoleccion/descargar_pdfs_articulos.py
```

### 2. Extracción con IA (Fase II)
Requiere una API key de Google Gemini configurada como variable de entorno:
```bash
export GOOGLE_API_KEY="tu_api_key_aquí"

# Screening cuantitativo/inferencial
python scripts/02_extraccion_ia/screening_cuant_inferencia_gemini.py

# Análisis y clasificación de artículos
python scripts/02_extraccion_ia/analizar_pdf_articulos.py
```

### 3. Simulación Monte Carlo (Fase III)
```bash
# Ejecutar simulación y generar tablas/figuras
python scripts/03_simulacion/calculos_tablas_figuras.py
```

### 4. Compilar el manuscrito
```bash
cd manuscrito
tectonic main.tex  # o latexmk -xelatex main.tex
```

## Datos principales

El archivo `datos/BASE_FINAL_ANALISIS_2026-04-03.csv` contiene las 628 observaciones con las siguientes variables principales:

| Variable | Descripción |
|---|---|
| `titulo` | Título del artículo |
| `revista` | Nombre de la revista |
| `pais` | País de la revista |
| `macroarea` | Macroárea disciplinar |
| `tipo_muestreo` | Tipo de muestreo declarado |
| `aplica_inferencia` | Si aplica estadística inferencial |
| `falla_fuerte` | Clasificación de Falla Fuerte (sí/no) |
| `debilidad_importante` | Clasificación de Debilidad Importante |
| `justificacion` | Justificación de la clasificación por IA |

## Hallazgos principales

| Categoría | n | % |
|---|---|---|
| **Falla Fuerte** | 245 | 39,0 |
| Debilidad Importante | 312 | 49,7 |
| Sin Falla Relevante | 71 | 11,3 |
| **Total** | **628** | **100,0** |

## Nota sobre reproducibilidad

- Los scripts de extracción con IA requieren acceso a la API de Google Gemini (modelo `gemini-2.5-flash`).
- Los PDFs de los artículos no se incluyen en el repositorio por razones de derechos de autor, pero pueden descargarse ejecutando los scripts de la Fase I.
- La base analítica final (`datos/BASE_FINAL_ANALISIS_2026-04-03.csv`) permite replicar todos los análisis estadísticos y la simulación Monte Carlo sin necesidad de re-ejecutar la extracción.

## Licencia

Este repositorio se distribuye con fines de transparencia científica y replicabilidad.

## Contacto

Diego Bernardo Meza Bogado — [dmeza.py@gmail.com](mailto:dmeza.py@gmail.com)
