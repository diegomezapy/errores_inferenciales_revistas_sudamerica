import os
import time
import json
import pandas as pd
import google.generativeai as genai
import tempfile
from PyPDF2 import PdfReader

# --- CONFIGURATION ---
API_KEY = "AIzaSyBNR_a_k2TBDKTMIXIxxB3vv6EhMeP3ai4"
genai.configure(api_key=API_KEY)

# Adjust this path based on where your downloaded PDFs are
PDF_DIR = r"G:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO\articulos_descargados"
# Main database to append the fields onto
DB_PATH = r"G:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO\bases_datos\BASEFINAL320articulos_CORREGIDO.xlsx"
OUTPUT_DB_PATH = r"G:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO\bases_datos\BASEFINAL320articulos_PROCESADO_IA.xlsx"
PROMPT_FILE = r"G:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO\bases_datos\promp_evaluadorIA.txt"

def load_prompt():
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def extract_text_from_pdf(pdf_path):
    text = ""
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    return text

def analyze_document_with_gemini(text, instructions):
    # Enforce JSON output in the prompt internally to reliably map columns
    system_prompt = f"""
Eres un investigador metodológico experto evaluando artículos académicos. 
Instrucciones del usuario:
{instructions}

IMPORTANTE: DEBES DEVOLVER EXCLUSIVAMENTE UN OBJETO JSON VÁLIDO. NO incluyas formato Markdown (como ```json). NO devuelvas texto adicional. 
El JSON debe ser un diccionario cuyas llaves sean exactamente los nombres de las columnas que solicitó el usuario:
- id_articulo
- nombre_archivo
- ruta_pdf_completa
- hipervinculo_pdf
- revista
- anio
- disciplina
- idioma
- titulo_completo
- subtitulo_sicorresponde
- resumen_completo
- objetivo_general
- frase_relacionada_a_inferencia
- frase_relacionada_a_muestreo
- tipo_variable_metrica
- tipo_estudio
- enfoque_metodologico
- diseno_estudio
- tamano_muestra
- es_cuantitativo_con_inferencia
- muestreo_probabilistico
- muestreo_no_probabilistico
- declara_tipo_muestreo
- declara_calculo_tamano_muestral
- usa_formulas_muestreo_probabilistico
- reporta_intervalos_confianza
- usa_margen_error_o_error_muestral
- extrapola_explicita_a_poblacion
- advierte_limites_por_muestreo_no_prob
- incumple_inferencia_con_muestreo_no_prob
- declara_software_estadistico
- tipo_software_estadistico
- usa_software_estadistico
- usa_software_open_source
- declara_librerias_paquetes
- detalle_librerias
- usa_metodos_cualitativos
- usa_tecnicas_recoleccion
- conclusion_sobre_la_falla_metodologica

Si no tienes información para un campo, usa un string vacío "".
"""
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    try:
        # To avoid context limits, truncate if it's absurdly long (gemini 1.5 flash has 1M context, should be fine, but we cap to 500k chars for safety)
        content_to_send = text[:500000] 
        response = model.generate_content([system_prompt, content_to_send])
        ans = response.text.replace("```json\n", "").replace("```", "").strip()
        data = json.loads(ans)
        return data
    except Exception as e:
        print(f"Error calling Gemini: {e}")
        return None

import concurrent.futures

def main():
    print("Loading database...")
    # Check if PROCESADO_IA exists to resume, otherwise load original
    if os.path.exists(OUTPUT_DB_PATH):
        print(f"Resuming from {OUTPUT_DB_PATH}")
        df = pd.read_excel(OUTPUT_DB_PATH)
    else:
        df = pd.read_excel(DB_PATH)
        
    prompt_instructions = load_prompt()
    
    # Get previously processed files to skip them
    processed_set = set()
    if 'nombre_archivo' in df.columns:
        processed_set = set(df['nombre_archivo'].dropna().tolist())
    
    pdf_files = []
    for root_dir in [PDF_DIR, os.path.join(PDF_DIR, "mega_descarga")]:
        if os.path.exists(root_dir):
            for f in os.listdir(root_dir):
                if f.lower().endswith(".pdf") and f not in processed_set:
                    pdf_files.append(os.path.join(root_dir, f))
                
    print(f"Found {len(pdf_files)} NEW PDF files to process (skipped {len(processed_set)}).")
    
    records = df.to_dict('records')
    
    def process_file(pdf):
        print(f"Processing {os.path.basename(pdf)}...")
        txt = extract_text_from_pdf(pdf)
        if len(txt) < 50:
            return None
            
        result = analyze_document_with_gemini(txt, prompt_instructions)
        
        if result:
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
                
            if isinstance(result, dict):
                result["nombre_archivo"] = os.path.basename(pdf)
                result["ruta_pdf_completa"] = pdf
                return result
        return None

    new_records = []
    
    # Process using a ThreadPoolExecutor
    print("Executing in parallel with 25 workers...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
        # submit all processing jobs
        future_to_pdf = {executor.submit(process_file, pdf): pdf for pdf in pdf_files}
        
        for i, future in enumerate(concurrent.futures.as_completed(future_to_pdf), 1):
            pdf = future_to_pdf[future]
            try:
                res = future.result()
                if res:
                    new_records.append(res)
                    print(f"[{i}/{len(pdf_files)}] Success extraction for: {os.path.basename(pdf)}")
                else:
                    print(f"[{i}/{len(pdf_files)}] Failed/Skipped: {os.path.basename(pdf)}")
            except Exception as exc:
                print(f"[{i}/{len(pdf_files)}] Error on {os.path.basename(pdf)} generated an exception: {exc}")
                
            # periodic saving per 50 to avoid data loss
            if i % 50 == 0 and len(new_records) > 0:
                temp_df = pd.DataFrame(new_records)
                temp_combined = pd.concat([df, temp_df], ignore_index=True)
                temp_combined.to_excel(OUTPUT_DB_PATH, index=False)
                print(f"---> Savepoint: wrote {len(new_records)} records to {OUTPUT_DB_PATH}")

    if new_records:
        df_new = pd.DataFrame(new_records)
        df_combined = pd.concat([df, df_new], ignore_index=True)
        df_combined.to_excel(OUTPUT_DB_PATH, index=False)
        print(f"\nFinished! Total {len(new_records)} items extracted successfully. Saved to {OUTPUT_DB_PATH}")
    else:
        print("No new records processed.")

if __name__ == "__main__":
    main()

