# config.py
from datetime import date

# =========================================================================
# 1. RUTAS DE ARCHIVOS Y DIRECTORIOS
# =========================================================================
RUTA_ZIPCODE = '/home/emanuel/DataSinteticaImss/data/zipcode.xls'
DIR_OUTPUT   = '/home/emanuel/DataSinteticaImss/output'
SALIDA_CSV   = f'{DIR_OUTPUT}/pacientes_sinteticos_cdmx.csv'
SALIDA_XLSX  = f'{DIR_OUTPUT}/pacientes_sinteticos_cdmx.xlsx'

# =========================================================================
# 2. CONFIGURACIÓN GENERAL DE LA SIMULACIÓN
# =========================================================================
SEED        = 42
N_PACIENTES = 10000

# =========================================================================
# 3. PARÁMETROS DEMOGRÁFICOS Y DE POBLACIÓN
# =========================================================================
EDAD_MINIMA          = 18
EDAD_MAXIMA          = 75
PROB_SEGUNDO_APELLIDO = 0.92

# Fuente: Censo de Población y Vivienda 2020, INEGI.
# Total CDMX: 9,209,944 habitantes — Mujeres: 52.2% | Hombres: 47.8%
PESOS_SEXO = {
    'Masculino':   0.478,
    'Femenino':    0.522,
    'Otro':        0.02,
    'Desconocido': 0.01
}

# =========================================================================
# 4. PARÁMETROS ANTROPOMÉTRICOS Y PROBABILIDADES (INEGI / ENSANUT)
# =========================================================================
ALTURA_MEDIA_MASCULINO = 170.0
ALTURA_MEDIA_FEMENINO  = 158.0
ALTURA_DESVIACION      = 6.0

ESTADISTICAS_INEGI = {
    'Adultos_30_59': {
        'Masculino': {'sobrepeso': 0.42, 'obesidad': 0.35, 'normal': 0.23},
        'Femenino':  {'sobrepeso': 0.37, 'obesidad': 0.46, 'normal': 0.17}
    },
    'Adultos_Mayores_60_Mas': {
        'Masculino': {'sobrepeso': 0.43, 'obesidad': 0.26, 'normal': 0.31},
        'Femenino':  {'sobrepeso': 0.38, 'obesidad': 0.40, 'normal': 0.22}
    }
}