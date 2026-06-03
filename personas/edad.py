# personas/edad.py
"""
Módulo de distribución de edades basado en el Censo de Población
y Vivienda 2020 del INEGI para la CDMX.

Lee el archivo Excel configurado en RUTA_CENSO_EDAD, extrae los grupos
quinquenales que se solapan con el rango [EDAD_MINIMA, EDAD_MAXIMA],
calcula probabilidades normalizadas por sexo y total, y expone la
función asignar_edad(sexo) para uso en personas.py.
"""
import random
import sys
import os
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


def _cargar_distribucion() -> pd.DataFrame:
    df = pd.read_excel(
        config.RUTA_CENSO_EDAD,
        header=0,
        usecols=[0, 1, 2, 3],
        names=['grupo', 'total', 'hombres', 'mujeres'],
        dtype=str
    )

    df = df.dropna(subset=['grupo'])
    df = df[~df['grupo'].str.contains(
        r'No especificado|especif|Grupo|Total', case=False, na=True, regex=True
    )]

    for col in ['total', 'hombres', 'mujeres']:
        df[col] = pd.to_numeric(
            df[col].str.replace(',', '', regex=False), errors='coerce'
        )
    df = df.dropna(subset=['total'])

    df['edad_min'] = df['grupo'].str.extract(r'^(\d+)').astype(int)
    df['edad_max'] = df['grupo'].str.extract(r'a (\d+)').astype(int, errors='ignore')
    df = df.dropna(subset=['edad_max'])
    df['edad_max'] = df['edad_max'].astype(int)

    # Incluir grupos que se solapan con [EDAD_MINIMA, EDAD_MAXIMA]
    mascara = (
        (df['edad_max'] >= config.EDAD_MINIMA) &
        (df['edad_min'] <= config.EDAD_MAXIMA)
    )
    df_filtrado = df[mascara].copy().reset_index(drop=True)

    if df_filtrado.empty:
        raise ValueError(
            f"No se encontraron grupos quinquenales que se solapen con "
            f"[{config.EDAD_MINIMA}, {config.EDAD_MAXIMA}] en {config.RUTA_CENSO_EDAD}."
        )

    df_filtrado['prob_total']   = df_filtrado['total']   / df_filtrado['total'].sum()
    df_filtrado['prob_hombres'] = df_filtrado['hombres'] / df_filtrado['hombres'].sum()
    df_filtrado['prob_mujeres'] = df_filtrado['mujeres'] / df_filtrado['mujeres'].sum()

    return df_filtrado


df_edad = _cargar_distribucion()

print(f"  [edad] Distribución quinquenal cargada — rango [{config.EDAD_MINIMA}-{config.EDAD_MAXIMA}] años:")
print(
    df_edad[['grupo', 'prob_total', 'prob_hombres', 'prob_mujeres']]
    .to_string(index=False, float_format=lambda x: f'{x:.4f}')
)
print()


def asignar_edad(sexo: str) -> int:
    """
    Muestrea un grupo quinquenal con probabilidad real del Censo INEGI 2020
    por sexo, y devuelve una edad entera dentro del rango del proyecto.
    """
    if sexo == 'Masculino':
        pesos = df_edad['prob_hombres'].tolist()
    elif sexo == 'Femenino':
        pesos = df_edad['prob_mujeres'].tolist()
    else:
        pesos = df_edad['prob_total'].tolist()

    grupo = random.choices(df_edad.to_dict('records'), weights=pesos, k=1)[0]

    edad_min_real = max(int(grupo['edad_min']), config.EDAD_MINIMA)
    edad_max_real = min(int(grupo['edad_max']), config.EDAD_MAXIMA)

    return random.randint(edad_min_real, edad_max_real)