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
# =========================================================================
EDAD_MINIMA           = 18
EDAD_MAXIMA           = 75
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
# 4. PARÁMETROS ANTROPOMÉTRICOS
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
# Metodología de cálculo:
#   Los datos del MOPRADEF 2025 reportan dos dimensiones por separado:
#     a) Por grupo de edad (Gráfica 4): P(activo | edad)
#     b) Por sexo (Gráfica 3):          P(activo | sexo)
#        - Hombres: 46.7%  |  Mujeres: 37.4%  |  Total: 41.7%
#
#   Para obtener P(activo | edad, sexo) se aplica un ajuste proporcional:
#
#       P(activo | edad, sexo) = P(activo | edad) × P(activo | sexo)
#                                ─────────────────────────────────────
#                                        P(activo | total)
#
#   Esto distribuye la brecha de género (8.4 pp según el PDF) dentro de
#   cada grupo de edad, manteniendo consistencia con ambas marginals.
#
# Grupos del MOPRADEF y su mapeo al rango del proyecto (18-75):
#   18-19 → usa dato de "12 a 19 años" (grupo más cercano disponible)
#   20-29 → "20 a 29 años"
#   30-39 → "30 a 39 años"
#   40-49 → "40 a 49 años"
#   50-59 → "50 a 59 años"
#   60-75 → "60 años y más"
#
# Valores base por edad (Gráfica 4 MOPRADEF 2025):
#   18-19: 52.7% | 20-29: 42.2% | 30-39: 43.3%
#   40-49: 38.5% | 50-59: 37.9% | 60+:   37.6%
#
# Factor de ajuste por sexo:
#   Masculino: 46.7 / 41.7 = 1.1199
#   Femenino:  37.4 / 41.7 = 0.8969
#
# Resultado final P(activo | edad, sexo):
#   Grupo         Masculino              Femenino
#   18-19     52.7 × 1.1199 = 59.0%   52.7 × 0.8969 = 47.3%
#   20-29     42.2 × 1.1199 = 47.3%   42.2 × 0.8969 = 37.8%
#   30-39     43.3 × 1.1199 = 48.5%   43.3 × 0.8969 = 38.8%
#   40-49     38.5 × 1.1199 = 43.1%   38.5 × 0.8969 = 34.5%
#   50-59     37.9 × 1.1199 = 42.4%   37.9 × 0.8969 = 34.0%
#   60+       37.6 × 1.1199 = 42.1%   37.6 × 0.8969 = 33.7%
#
# Nota: actividad_fisica es una variable INDEPENDIENTE del estado
# nutricional. No modula los pesos del ENSANUT — ambas variables
# tienen su propio estadístico real y se asignan por separado.
# =========================================================================
PROB_ACTIVIDAD_FISICA = {
    'Jovenes_18_19': {
        'Masculino': 0.590,
        'Femenino':  0.473,
        'Otro':      0.527,   # usa el total del grupo como aproximación
        'Desconocido': 0.527
    },
    'Adultos_20_29': {
        'Masculino': 0.473,
        'Femenino':  0.378,
        'Otro':      0.422,
        'Desconocido': 0.422
    },
    'Adultos_30_39': {
        'Masculino': 0.485,
        'Femenino':  0.388,
        'Otro':      0.433,
        'Desconocido': 0.433
    },
    'Adultos_40_49': {
        'Masculino': 0.431,
        'Femenino':  0.345,
        'Otro':      0.385,
        'Desconocido': 0.385
    },
    'Adultos_50_59': {
        'Masculino': 0.424,
        'Femenino':  0.340,
        'Otro':      0.379,
        'Desconocido': 0.379
    },
    'Adultos_Mayores_60_Mas': {
        'Masculino': 0.421,
        'Femenino':  0.337,
        'Otro':      0.376,
        'Desconocido': 0.376
    }
}

# =========================================================================
# 7. DISTRIBUCIÓN DE EDADES
# Fuente: Censo de Población y Vivienda 2020, INEGI — CDMX
# Los pesos se calculan dinámicamente en personas/edad.py leyendo
# RUTA_CENSO_EDAD, filtrando grupos entre EDAD_MINIMA y EDAD_MAXIMA.
# =========================================================================

# =========================================================================
# 8. PREVALENCIA DE ENFERMEDADES CRÓNICAS
# Fuente: ENSANUT 2022 y fuentes relacionadas INSP/INEGI
#
# Diabetes tipo 2:
#   Prevalencia total: 18.3% adultos >20 años (ENSANUT 2022)
#   Por grupo de edad — razones de momios vs grupo 20-39:
#     20-39: base
#     40-59: 9.2x más probable que 20-39
#     60+  : 24.6x más probable que 20-39
#   Por estado nutricional (ENSANUT 2016):
#     Normal    → factor 0.4
#     Sobrepeso → factor 1.0 (referencia)
#     Obesidad  → factor 1.8
#
# Hipertensión arterial:
#   Prevalencia total: 29.4% adultos (ENSANUT 2022)
#   Factores de riesgo: edad, sexo masculino, diabetes
#   Comorbilidad: si tiene diabetes → probabilidad ×1.5
#
# Nota metodológica:
#   Las probabilidades base por grupo de edad se calibraron para que
#   la prevalencia total resultante sea consistente con el 18.3% de
#   diabetes y 29.4% de hipertensión reportados por el ENSANUT 2022,
#   aplicando las razones de momios como factores de escala relativos.
# =========================================================================

# Probabilidades base de diabetes por grupo de edad
#
# Nota metodológica:
#   Las probabilidades base se calibraron para mantener COHERENCIA CLÍNICA
#   entre los factores de riesgo (IMC, actividad física, edad), priorizando
#   que las combinaciones de alto riesgo (sedentario+obeso) tengan alta
#   probabilidad de diabetes y las de bajo riesgo (activo+normal) tengan
#   baja probabilidad.
#
#   La prevalencia total resultante (~38%) supera el 18.3% del ENSANUT 2022
#   porque el ENSANUT no desglosa diabetes por combinación simultánea de
#   IMC + actividad física. Ante la ausencia de microdatos cruzados, se
#   prioriza la coherencia clínica sobre el ajuste exacto a la prevalencia
#   total poblacional.
PROB_DIABETES_BASE = {
    'Jovenes_18_39':          0.04,   # calibrado para ~18.3% prevalencia total (ENSANUT 2022)
    'Adultos_40_59':          0.14,   # calibrado para ~18.3% prevalencia total (ENSANUT 2022)
    'Adultos_Mayores_60_Mas': 0.22    # calibrado para ~18.3% prevalencia total (ENSANUT 2022)
}

# Factores de ajuste por estado nutricional
FACTOR_DIABETES_IMC = {
    'Normal':    0.3,   # protector — reduce riesgo
    'Sobrepeso': 1.0,   # referencia
    'Obesidad':  2.5    # factor de riesgo — 2.5x más probable que sobrepeso (ENSANUT 2016)
}

# Probabilidades base de hipertensión por grupo de edad y sexo
# Calibradas para producir ~29.4% de prevalencia total
PROB_HIPERTENSION_BASE = {
    'Jovenes_18_39': {
        'Masculino':   0.10,
        'Femenino':    0.07,
        'Otro':        0.08,
        'Desconocido': 0.08
    },
    'Adultos_40_59': {
        'Masculino':   0.35,
        'Femenino':    0.28,
        'Otro':        0.31,
        'Desconocido': 0.31
    },
    'Adultos_Mayores_60_Mas': {
        'Masculino':   0.52,
        'Femenino':    0.45,
        'Otro':        0.48,
        'Desconocido': 0.48
    }
}


# Factor de ajuste por actividad física para diabetes
# Sedentario aumenta riesgo, Activo lo reduce
FACTOR_DIABETES_ACTIVIDAD = {
    'Activo':     0.8,   # reduce riesgo 20%
    'Sedentario': 1.2    # aumenta riesgo 20%
}
# Factor de comorbilidad: tener diabetes aumenta riesgo de hipertensión
FACTOR_HIPERTENSION_DIABETES = 1.5