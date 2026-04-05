# Errores Inferenciales Críticos en Estudios Cuantitativos Sudamericanos

> **Repositorio de respaldo y evidencia para el artículo sometido a la revista *DADOS — Revista de Ciências Sociais*.**

## Resumen

Este repositorio contiene el código fuente LaTeX, figuras, tablas y scripts de soporte del artículo:

> **Errores inferenciales críticos en estudios cuantitativos publicados en revistas sudamericanas de acceso abierto**
>
> Diego Bernardo Meza Bogado  
> Facultad de Ciencias Exactas y Naturales, Universidad Nacional de Asunción (FACEN-UNA)

El estudio estima la prevalencia de fallas inferenciales críticas en 628 artículos cuantitativos publicados en revistas sudamericanas de acceso abierto, y cuantifica mediante simulación Monte Carlo el impacto de aplicar estadística inferencial sobre muestras no probabilísticas.

## Estructura del repositorio

```
├── manuscrito/                 # Código fuente LaTeX (formato DADOS)
│   ├── main.tex               # Archivo principal del manuscrito
│   ├── introduccion.tex       # Sección: Introducción
│   ├── marcoteorico.tex       # Sección: Marco teórico
│   ├── metodologia.tex        # Sección: Datos y métodos
│   ├── resultados.tex         # Sección: Resultados
│   ├── consideraciones.tex    # Sección: Consideraciones finales
│   ├── apendices.tex          # Apéndices A, B y C
│   ├── referencias_dados.tex  # Bibliografía
│   ├── fig_flujo_corpus_sintetico.tex  # Diagrama TikZ de flujo metodológico
│   ├── latexmkrc              # Configuración de compilación
│   └── tablasyfig/            # Figuras y tablas
│       ├── fig2_distribucion_porcentual_por_area.png
│       ├── fig_simulacion_resultados.png
│       ├── fig_flujo_standalone.pdf
│       ├── figura_metodologia_dual.png
│       └── [tablas .tex adicionales]
├── scripts/
│   └── generar_diagrama_metodologia.py  # Generador del diagrama metodológico
├── .gitignore
└── README.md
```

## Compilación

El manuscrito se compila con cualquier distribución TeX moderna. Desde el directorio `manuscrito/`:

```bash
# Con latexmk (recomendado)
latexmk -xelatex main.tex

# O con tectonic
tectonic main.tex
```

**Requisitos:** `newtxtext`, `newtxmath`, `natbib`, `booktabs`, `longtable`, `tikz`, `pgfplots`, `siunitx`, `hyperref`, `fancyhdr`, `lastpage`.

## Hallazgos principales

| Categoría | n | % |
|---|---|---|
| **Falla Fuerte** | 245 | 39,0 |
| Debilidad Importante | 312 | 49,7 |
| Sin Falla Relevante | 71 | 11,3 |
| **Total** | **628** | **100,0** |

- El **88,7%** de los artículos aplica inferencia estadística sobre diseños muestrales no probabilísticos.
- La simulación Monte Carlo confirma que la selección por conveniencia induce **sesgos irreversibles**.
- Los diseños probabilísticos (MAS-SR y estratificado) mantienen cobertura próxima a la nominal (93–96%).

## Licencia

Este repositorio se distribuye con fines académicos y de transparencia científica. El contenido del manuscrito es propiedad intelectual del autor.

## Contacto

Diego Bernardo Meza Bogado — [dmeza.py@gmail.com](mailto:dmeza.py@gmail.com)
