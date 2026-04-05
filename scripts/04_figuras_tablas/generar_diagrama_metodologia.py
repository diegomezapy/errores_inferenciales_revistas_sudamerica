import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import sys

# Configuración de fuente y tamaño
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans']

fig, ax = plt.subplots(figsize=(12, 9))
ax.axis('off')

# Colores profesional
color_bg_auditoria = '#E8F0FE'
color_edge_auditoria = '#1A73E8'
color_bg_simulacion = '#FCE8E6'
color_edge_simulacion = '#D93025'
color_bg_final = '#E6F4EA'
color_edge_final = '#1E8E3E'
color_text = '#202124'
color_arrow = '#5F6368'

# Dimensiones cajas
box_w = 4.2
box_h = 0.8
spacing_y = 1.3

# Función helper para dibujar cajas
def draw_box(x, y, text, bg_color, edge_color, is_bold=False):
    rect = patches.FancyBboxPatch(
        (x - box_w/2, y - box_h/2), box_w, box_h, 
        boxstyle="round,pad=0.1,rounding_size=0.15",
        edgecolor=edge_color, facecolor=bg_color, linewidth=1.5, zorder=2
    )
    ax.add_patch(rect)
    
    font_weight = 'bold' if is_bold else 'normal'
    
    # Separar título de la descripción
    parts = text.split('\n', 1)
    if len(parts) > 1:
        ax.text(x, y + 0.15, parts[0], ha='center', va='center', fontsize=10, 
                fontweight='bold', color=color_text, zorder=3)
        ax.text(x, y - 0.15, parts[1], ha='center', va='center', fontsize=9, 
                color=color_text, zorder=3)
    else:
        ax.text(x, y, text, ha='center', va='center', fontsize=10, 
                fontweight=font_weight, color=color_text, zorder=3)

# Función helper para flechas
def draw_arrow(x1, y1, x2, y2, color=color_arrow, custom_style=False):
    if custom_style:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(facecolor=color, edgecolor=color, alpha=0.9,
                                   width=2, headwidth=8, headlength=10, shrink=0.02),
                    zorder=1)
    else:
        ax.annotate('', xy=(x2, y2 + box_h/2 + 0.05), xytext=(x1, y1 - box_h/2 - 0.05),
                    arrowprops=dict(facecolor=color, edgecolor=color, alpha=0.9,
                                   width=1.5, headwidth=7, headlength=8),
                    zorder=1)

# --- Coordenadas ---
x_aud = 3
x_sim = 8.5
y_start = 8

# Textos Auditoría — NÚMEROS ACTUALIZADOS
aud_texts = [
    "1. Universo Editorial\nRevistas sudamericanas de acceso abierto\nindexadas en DOAJ (códigos LCC)",
    "2. Selección Multietápica\nMuestreo estratificado proporcional\nde revistas y artículos (2018–2025)",
    "3. Recolección Automatizada\nConsulta API DOAJ + descarga masiva\nde PDFs (n = 2.191 artículos)",
    "4. Extracción por IA\nGemini 2.5 Flash + validación JSON\n(pdfplumber + Pydantic)",
    "5. Depuración y Elegibilidad\nExclusión de artículos sin inferencia\n(–1.563 artículos excluidos)",
    "6. Clasificación Analítica Final\nFalla Fuerte / Debilidad Importante /\nSin Falla (n = 628 artículos)"
]

# Textos Simulación
sim_texts = [
    "1. Población Finita Conocida\nN = 279.152, parámetros fijos (μ, p)",
    "2. Planificación por Precisión\nTamaños muestrales vía AIPE y CPF",
    "3. Diseño de Muestreo in Silico\nProbabilístico (MAS-SR, Estratificado)\nvs. No Probabilístico (Conveniencia)",
    "4. Replicación (R = 10.000)\nCobertura, Sesgo Relativo y RMSE"
]

# Títulos de columnas
ax.text(x_aud, y_start + 0.9, "FASE 1: AUDITORÍA DOCUMENTAL\n(Diagnóstico observacional)", 
        ha='center', va='center', fontsize=11, fontweight='bold', color=color_edge_auditoria)
ax.text(x_sim, y_start + 0.9, "FASE 2: SIMULACIÓN MONTE CARLO\n(Cuantificación de riesgo)", 
        ha='center', va='center', fontsize=11, fontweight='bold', color=color_edge_simulacion)

# Dibujar Auditoría
y_current_aud = y_start
for i, txt in enumerate(aud_texts):
    draw_box(x_aud, y_current_aud, txt, color_bg_auditoria, color_edge_auditoria)
    if i < len(aud_texts) - 1:
        draw_arrow(x_aud, y_current_aud, x_aud, y_current_aud - spacing_y)
    y_current_aud -= spacing_y

# Dibujar Simulación (Alineada para terminar al mismo nivel que auditoría)
y_current_sim = y_start - spacing_y * 0.5  # Empieza un poco más abajo
spacing_sim = (len(aud_texts)-1) * spacing_y / (len(sim_texts)-1)

for i, txt in enumerate(sim_texts):
    draw_box(x_sim, y_current_sim, txt, color_bg_simulacion, color_edge_simulacion)
    if i < len(sim_texts) - 1:
        draw_arrow(x_sim, y_current_sim, x_sim, y_current_sim - spacing_sim)
    y_current_sim -= spacing_sim

# Restaurar y_current_aud y y_current_sim para convergencia
y_last_aud = y_start - (len(aud_texts)-1)*spacing_y
y_last_sim = y_start - spacing_y * 0.5 - (len(sim_texts)-1)*spacing_sim
y_final = min(y_last_aud, y_last_sim) - spacing_y * 1.2

# Caja Final
draw_box((x_aud + x_sim)/2, y_final, "SÍNTESIS Y CONCLUSIONES\nImplicancias inferenciales y lineamientos editoriales", 
         color_bg_final, color_edge_final)

# Flechas convergentes
draw_arrow(x_aud, y_last_aud - box_h/2, (x_aud + x_sim)/2 - 0.5, y_final + box_h/2, color=color_edge_auditoria, custom_style=True)
draw_arrow(x_sim, y_last_sim - box_h/2, (x_aud + x_sim)/2 + 0.5, y_final + box_h/2, color=color_edge_simulacion, custom_style=True)

# Guardar
ax.set_xlim(0, 11.5)
ax.set_ylim(y_final - 1, y_start + 1.5)

# Output path from command line argument or default
if len(sys.argv) > 1:
    output_path = sys.argv[1]
else:
    output_path = 'figura_metodologia_dual'

plt.tight_layout()
plt.savefig(f'{output_path}.png', format='png', bbox_inches='tight', dpi=300)
print(f"Generado exitosamente: {output_path}.png")
