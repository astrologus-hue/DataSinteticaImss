# config.py
from datetime import date

# =========================================================================
# 1. RUTAS DE ARCHIVOS Y DIRECTORIOS
# =========================================================================
RUTA_ZIPCODE    = '/home/emanuel/DataSinteticaImss/data/zipcode.xls'
RUTA_CENSO_EDAD = '/home/emanuel/DataSinteticaImss/data/Poblacion_CDMX.xlsx'
DIR_OUTPUT      = '/home/emanuel/DataSinteticaImss/output'
SALIDA_CSV      = f'{DIR_OUTPUT}/pacientes_sinteticos_cdmx.csv'
SALIDA_XLSX     = f'{DIR_OUTPUT}/pacientes_sinteticos_cdmx.xlsx'

# =========================================================================
# 2. CONFIGURACIÓN GENERAL DE LA SIMULACIÓN
# =========================================================================
SEED        = 42
N_PACIENTES = 10000

# =========================================================================
# 3. PARÁMETROS DEMOGRÁFICOS Y DE POBLACIÓN
# Fuente: Censo de Población y Vivienda 2020, INEGI.
# Total CDMX: 9,209,944 habitantes — Mujeres: 52.2% | Hombres: 47.8%
# =========================================================================
EDAD_MINIMA           = 18
EDAD_MAXIMA           = 75
PROB_SEGUNDO_APELLIDO = 0.92

PESOS_SEXO = {
    'Masculino':   0.478,
    'Femenino':    0.522,
    'Otro':        0.02,
    'Desconocido': 0.01
}

# =========================================================================
# 4. PARÁMETROS ANTROPOMÉTRICOS
# Fuente: Parámetros antropométricos generales México
# =========================================================================
ALTURA_MEDIA_MASCULINO = 170.0
ALTURA_MEDIA_FEMENINO  = 158.0
ALTURA_DESVIACION      = 6.0

# =========================================================================
# 5. ESTADÍSTICOS DE ESTADO NUTRICIONAL POR GRUPO DE EDAD Y SEXO
# Fuente: INEGI/INSP. Encuesta Nacional de Salud y Nutrición (ENSANUT) 2018.
#
# Nota metodológica:
#   - sobrepeso y obesidad provienen directamente de las gráficas ENSANUT.
#   - normal = 1.0 - sobrepeso - obesidad
#   - Grupo 'Jovenes_18_19': datos de "12 a 19 años" del ENSANUT.
#   - Grupo 'Adultos_Mayores_60_Mas': sobrepeso de "20 años y más"
#     pues la gráfica no desglosa más allá.
# =========================================================================
ESTADISTICAS_INEGI = {
    'Jovenes_18_19': {
        'Masculino': {'sobrepeso': 0.21, 'obesidad': 0.15, 'normal': 0.64},
        'Femenino':  {'sobrepeso': 0.27, 'obesidad': 0.14, 'normal': 0.59}
    },
    'Adultos_20_29': {
        'Masculino': {'sobrepeso': 0.42, 'obesidad': 0.24, 'normal': 0.34},
        'Femenino':  {'sobrepeso': 0.37, 'obesidad': 0.26, 'normal': 0.37}
    },
    'Adultos_30_59': {
        'Masculino': {'sobrepeso': 0.42, 'obesidad': 0.35, 'normal': 0.23},
        'Femenino':  {'sobrepeso': 0.37, 'obesidad': 0.46, 'normal': 0.17}
    },
    'Adultos_Mayores_60_Mas': {
        'Masculino': {'sobrepeso': 0.42, 'obesidad': 0.26, 'normal': 0.32},
        'Femenino':  {'sobrepeso': 0.37, 'obesidad': 0.40, 'normal': 0.23}
    }
}

# =========================================================================
# 6. PROBABILIDAD DE ACTIVIDAD FÍSICA POR GRUPO DE EDAD Y SEXO
# Fuente: INEGI. Módulo de Práctica Deportiva y Ejercicio Físico
#         (MOPRADEF) 2025. Comunicado de Prensa 6/26.
#
# Metodología:
#   P(activo | edad, sexo) = P(activo | edad) × P(activo | sexo)
#                            ─────────────────────────────────────
#                                    P(activo | total)
#
#   Valores base por edad (Gráfica 4 MOPRADEF 2025):
#     18-19: 52.7% | 20-29: 42.2% | 30-39: 43.3%
#     40-49: 38.5% | 50-59: 37.9% | 60+:   37.6%
#
#   Factor de ajuste por sexo:
#     Masculino: 46.7 / 41.7 = 1.1199
#     Femenino:  37.4 / 41.7 = 0.8969
# =========================================================================
PROB_ACTIVIDAD_FISICA = {
    'Jovenes_18_19': {
        'Masculino': 0.590, 'Femenino': 0.473,
        'Otro': 0.527,      'Desconocido': 0.527
    },
    'Adultos_20_29': {
        'Masculino': 0.473, 'Femenino': 0.378,
        'Otro': 0.422,      'Desconocido': 0.422
    },
    'Adultos_30_39': {
        'Masculino': 0.485, 'Femenino': 0.388,
        'Otro': 0.433,      'Desconocido': 0.433
    },
    'Adultos_40_49': {
        'Masculino': 0.431, 'Femenino': 0.345,
        'Otro': 0.385,      'Desconocido': 0.385
    },
    'Adultos_50_59': {
        'Masculino': 0.424, 'Femenino': 0.340,
        'Otro': 0.379,      'Desconocido': 0.379
    },
    'Adultos_Mayores_60_Mas': {
        'Masculino': 0.421, 'Femenino': 0.337,
        'Otro': 0.376,      'Desconocido': 0.376
    }
}

# =========================================================================
# 7. DISTRIBUCIÓN DE EDADES
# Fuente: Censo de Población y Vivienda 2020, INEGI — CDMX
# Los pesos se calculan dinámicamente en personas/edad.py leyendo
# RUTA_CENSO_EDAD, filtrando grupos entre EDAD_MINIMA y EDAD_MAXIMA.
# =========================================================================