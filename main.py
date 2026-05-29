# main.py
import os
import time
import pandas as pd
import config as proyecto_config

def ejecutar_pipeline():
    print("=" * 70)
    print(" INICIANDO PIPELINE DE GENERACIÓN DE DATOS SINTÉTICOS - IMSS")
    print("=" * 70)
    
    tiempo_inicio = time.time()
    
    print(f"[*] Cargando catálogo de códigos postales y configuraciones...")
    # Importación adaptada a la nueva ruta
    from personas import personas
    
    print("\n[*] Validando la integridad de la tabla unificada generada...")
    
    if os.path.exists(proyecto_config.SALIDA_CSV):
        df_muestra = pd.read_csv(proyecto_config.SALIDA_CSV, nrows=5)
        df_muestra['estatura_cm'] = df_muestra['estatura_cm'].astype(int)
        
        total_filas = len(pd.read_csv(proyecto_config.SALIDA_CSV, usecols=[0]))
        
        print(f"\n[✓] ¡ÉXITO! Se ha consolidado una sola tabla con {total_filas:,} registros.")
        print("-" * 70)
        print("MUESTRA DE LAS COLUMNAS Y DATOS ANTROPOMÉTRICOS GENERADOS:")
        print("-" * 70)
        
        columnas_vista = ['nss', 'nombre', 'sexo', 'edad', 'estatura_cm', 'imc', 'peso_kg', 'estado_nutricional', 'municipio']
        print(df_muestra[columnas_vista].to_string(index=False))
        print("-" * 70)
    else:
        print("\n[X] ERROR: No se pudo localizar la tabla unificada de salida.")
        return

    tiempo_total = time.time() - tiempo_inicio
    print(f"[*] Archivos guardados en: {proyecto_config.DIR_OUTPUT}")
    print(f"[✓] Proceso completado en: {tiempo_total:.2f} segundos.")
    print("=" * 70)

if __name__ == "__main__":
    ejecutar_pipeline()