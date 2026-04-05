import pandas as pd

print("Starting analysis...")

# Read the Claude validation file
claude_file = r'g:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO\validacion_manual_claude_2026-04-03.csv'
base_file = r'g:\Mi unidad\DECENA_FACEN\04_INVESTIGACION_REPO\BASE_FINAL_ANALISIS_2026-04-03.csv'

try:
    # Read Claude file
    df_claude = pd.read_csv(claude_file, sep=';')
    print(f'Claude file has {len(df_claude)} rows')
    print('Claude columns:', df_claude.columns.tolist())

    # Read BASE file
    df_base = pd.read_csv(base_file, sep=';')
    print(f'BASE file has {len(df_base)} rows')
    print('BASE columns:', df_base.columns.tolist())

    # Check if nombre_archivo exists in both
    if 'nombre_archivo' in df_claude.columns and 'nombre_archivo' in df_base.columns:
        # Merge on nombre_archivo
        merged = pd.merge(df_claude, df_base[['nombre_archivo', 'clasificacion_original', 'clasificacion_final']],
                         on='nombre_archivo', how='inner')
        print(f'Merged dataframe has {len(merged)} rows')

        # Compare classifications
        if len(merged) > 0:
            # Compare Gemini (clasificacion_gemini) with BASE clasificacion_original
            gemini_match = (merged['clasificacion_gemini'] == merged['clasificacion_original']).sum()
            print(f'Gemini classifications match BASE original: {gemini_match}/{len(merged)} = {gemini_match/len(merged)*100:.1f}%')

            # Compare Claude with BASE final
            claude_match = (merged['clasificacion_claude'] == merged['clasificacion_final']).sum()
            print(f'Claude classifications match BASE final: {claude_match}/{len(merged)} = {claude_match/len(merged)*100:.1f}%')

            # Compare Claude with Gemini
            claude_gemini_match = (merged['clasificacion_claude'] == merged['clasificacion_gemini']).sum()
            print(f'Claude matches Gemini: {claude_gemini_match}/{len(merged)} = {claude_gemini_match/len(merged)*100:.1f}%')

            # Show some examples
            print('\nFirst 10 comparisons:')
            for idx in range(min(10, len(merged))):
                row = merged.iloc[idx]
                print(f'{row["nombre_archivo"]}: Gemini={row["clasificacion_gemini"]}, Claude={row["clasificacion_claude"]}, BASE_orig={row["clasificacion_original"]}, BASE_final={row["clasificacion_final"]}')

            # Detailed comparison
            print('\nDetailed comparison by category:')
            categories = ['Falla fuerte', 'Debilidad importante', 'Sin falla relevante', 'No aplica', 'Sin texto disponible']
            for cat in categories:
                if cat in merged['clasificacion_gemini'].values or cat in merged['clasificacion_claude'].values:
                    gemini_count = (merged['clasificacion_gemini'] == cat).sum()
                    claude_count = (merged['clasificacion_claude'] == cat).sum()
                    base_orig_count = (merged['clasificacion_original'] == cat).sum()
                    base_final_count = (merged['clasificacion_final'] == cat).sum()
                    print(f'{cat}: Gemini={gemini_count}, Claude={claude_count}, BASE_orig={base_orig_count}, BASE_final={base_final_count}')

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
