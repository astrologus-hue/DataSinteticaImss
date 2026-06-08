# personas/enfermedades.py
"""
Módulo de asignación de enfermedades crónicas y comorbilidades.

Asigna al paciente sus condiciones de salud INICIALES al momento
de la generación del dataset. NO modela evolución temporal
(eso es responsabilidad de historial.py).

Enfermedades modeladas:
    1. Diabetes tipo 2 (DM2)
    2. Hipertensión arterial (HTA)
    3. Dislipidemia (HCL)

Fuentes estadísticas:
    ENSANUT 2022        — prevalencia DM2 18.3%, prediabetes 22.1%
    ENSANUT 2022        — 31.7% no diagnosticados (65.6% en <40, 18.1% en 60+)
    ENSANUT 2021-2024   — CDMX región Centro: 21.1% prevalencia DM2
    ENSANUT 2022        — RM obesidad→DM2 = 1.7
    ENSANUT 2022        — hipertensión 29.4%, 43.9% no diagnosticados
    NOM-015-SSA2-2010   — rangos glucosa, HbA1c, criterios diagnósticos
    ENSA 2004 CDMX      — P(HCL|DM2) = 55.2% independiente del IMC
    ENSA 2004 CDMX      — P(HTA|DM2) = 46%
    ENSA 2004 CDMX      — P(HCL|HTA sin DM2) = 52.5%
    ENSA 2004 CDMX      — OR HTA→HCL = 1.35, OR DM2→HCL = 1.24

Momento del diagnóstico:
    Determina el valor inicial de glucosa/HbA1c para el AR(1).
    Fuente: ENSANUT 2022 — no diagnóstico por edad:
        <40 años  : 65.6% no saben
        General   : 31.7%
        60+ años  : 18.1%
    Fuente: ENSANUT 2021-2024 — CDMX: <30% con control glucémico
"""
import random
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


# ===========================================================================
# PARÁMETROS DE DIABETES TIPO 2
# ===========================================================================

# Probabilidad base por grupo de edad — calibrada para ~18.3% total (ENSANUT 2022)
PROB_DIABETES_BASE = {
    'Jovenes_18_39':          0.04,
    'Adultos_40_59':          0.14,
    'Adultos_Mayores_60_Mas': 0.22
}

# Factor por estado nutricional — RM obesidad=1.7 (ENSANUT 2022)
FACTOR_DIABETES_IMC = {
    'Normal':    0.3,
    'Sobrepeso': 1.0,
    'Obesidad':  1.7
}

# Factor por actividad física (NOM-015-SSA2: sedentarismo es factor de riesgo)
FACTOR_DIABETES_ACTIVIDAD = {
    'Activo':     0.8,
    'Sedentario': 1.2
}


# ===========================================================================
# PARÁMETROS DE HIPERTENSIÓN ARTERIAL
# ===========================================================================

# Probabilidad base por grupo de edad y sexo — calibrada para ~29.4% (ENSANUT 2022)
PROB_HIPERTENSION_BASE = {
    'Jovenes_18_39': {
        'Masculino': 0.10, 'Femenino': 0.07,
        'Otro': 0.08,      'Desconocido': 0.08
    },
    'Adultos_40_59': {
        'Masculino': 0.35, 'Femenino': 0.28,
        'Otro': 0.31,      'Desconocido': 0.31
    },
    'Adultos_Mayores_60_Mas': {
        'Masculino': 0.52, 'Femenino': 0.45,
        'Otro': 0.48,      'Desconocido': 0.48
    }
}

# P(HTA | DM2) = 46% — ENSA 2004 CDMX (120,005 adultos)
# Se usa directamente si el paciente tiene diabetes
PROB_HTA_DADO_DM2 = 0.46


# ===========================================================================
# PARÁMETROS DE DISLIPIDEMIA (HIPERCOLESTEROLEMIA)
# ===========================================================================
# Fuente: ENSA 2004 CDMX — Encuesta Nacional de Salud 120,005 adultos
#
# Hallazgo clave del PDF:
#   En DIABÉTICOS: P(HCL|DM2) = 55.2%, INDEPENDIENTE del IMC
#     → el gradiente de cambio por IMC es mínimo (Tabla V del PDF)
#     → se usa probabilidad casi constante sin factor IMC
#   En NO DIABÉTICOS: el IMC sí afecta significativamente:
#     IMC <25  → 34.1%
#     IMC 25-29.9 → 45.9%
#     IMC ≥30  → 47.3%
#   En HIPERTENSOS sin DM2: P(HCL|HTA) = 52.5% (Tabla I del PDF)

PROB_HCL_DADO_DM2 = 0.552        # 55.2% — ENSA 2004, independiente de IMC

PROB_HCL_SIN_DM2_POR_IMC = {     # ENSA 2004 Tabla I — población sin DM2
    'Normal':    0.341,
    'Sobrepeso': 0.459,
    'Obesidad':  0.473
}

PROB_HCL_DADO_HTA_SIN_DM2 = 0.525  # 52.5% — ENSA 2004 Tabla I


# ===========================================================================
# MOMENTO DEL DIAGNÓSTICO — por grupo de edad
# Fuente: ENSANUT 2022 — no diagnóstico por edad
#         ENSANUT 2021-2024 — CDMX: <30% con control
# ===========================================================================
MOMENTO_DIAGNOSTICO_POR_EDAD = {
    'menor_40': {
        'muy_tardio': 0.656,   # 65.6% no saben — ENSANUT 2022
        'tardio':     0.244,
        'temprano':   0.070,
        'oportuno':   0.030,
    },
    'adulto_40_59': {
        'muy_tardio': 0.317,   # 31.7% no saben — ENSANUT 2022
        'tardio':     0.353,
        'temprano':   0.200,
        'oportuno':   0.130,
    },
    'adulto_mayor_60': {
        'muy_tardio': 0.181,   # 18.1% no saben — ENSANUT 2022
        'tardio':     0.399,
        'temprano':   0.240,
        'oportuno':   0.180,
    },
}

# Rangos de glucosa y HbA1c por momento del diagnóstico (NOM-015-SSA2-2010)
RANGOS_MOMENTO = {
    'oportuno':   {'glucosa': (100, 125), 'hba1c': (5.7, 6.4)},
    'temprano':   {'glucosa': (126, 160), 'hba1c': (6.5, 7.5)},
    'tardio':     {'glucosa': (161, 220), 'hba1c': (7.5, 9.5)},
    'muy_tardio': {'glucosa': (221, 320), 'hba1c': (9.5, 13.0)},
}


# ===========================================================================
# FUNCIONES AUXILIARES
# ===========================================================================

def _grupo_enfermedad(edad: int) -> str:
    """Mapea edad al grupo epidemiológico."""
    if edad <= 39:
        return 'Jovenes_18_39'
    elif edad <= 59:
        return 'Adultos_40_59'
    else:
        return 'Adultos_Mayores_60_Mas'


def _grupo_edad_diagnostico(edad: int) -> str:
    """Mapea edad al grupo de momento del diagnóstico."""
    if edad < 40:
        return 'menor_40'
    elif edad <= 59:
        return 'adulto_40_59'
    else:
        return 'adulto_mayor_60'


def _asignar_momento_diagnostico(edad: int) -> dict:
    """
    Determina el momento del diagnóstico y valores iniciales para AR(1).

    Fuentes:
        ENSANUT 2022       — no diagnóstico por edad
        ENSANUT 2021-2024  — CDMX: <30% con control glucémico
        NOM-015-SSA2-2010  — rangos glucosa y HbA1c
    """
    grupo   = _grupo_edad_diagnostico(edad)
    probs   = MOMENTO_DIAGNOSTICO_POR_EDAD[grupo]
    momento = random.choices(list(probs.keys()), weights=list(probs.values()), k=1)[0]
    rangos  = RANGOS_MOMENTO[momento]

    return {
        'momento':         momento,
        'glucosa_inicial': round(random.uniform(*rangos['glucosa']), 1),
        'hba1c_inicial':   round(random.uniform(*rangos['hba1c']),   1),
        'diagnosticado':   momento != 'muy_tardio',
    }


# ===========================================================================
# FUNCIÓN PRINCIPAL
# ===========================================================================

def asignar_enfermedades(edad: int, sexo: str,
                          estado_nutricional: str,
                          actividad_fisica: str) -> dict:
    """
    Asigna DM2, HTA y dislipidemia al paciente con sus comorbilidades.

    Lógica de comorbilidades:
        1. DM2  → prob_base × factor_IMC × factor_actividad
        2. HTA  → si tiene DM2: P(HTA|DM2) = 46% (ENSA 2004)
                  si no tiene DM2: prob_base(edad, sexo) (ENSANUT 2022)
        3. HCL  → si tiene DM2: P(HCL|DM2) = 55.2% INDEPENDIENTE del IMC
                  si tiene HTA sin DM2: P(HCL|HTA) = 52.5% (ENSA 2004)
                  si no tiene ninguna: P(HCL) por IMC (ENSA 2004 Tabla I)

    Parámetros
    ----------
    edad               : int
    sexo               : str — Masculino | Femenino | Otro | Desconocido
    estado_nutricional : str — Normal | Sobrepeso | Obesidad
    actividad_fisica   : str — Activo | Sedentario

    Retorna
    -------
    dict:
        diabetes          : Sí | No
        hipertension      : Sí | No
        dislipidemia      : Sí | No
        momento_dx        : str  (solo si diabetes=Sí)
        glucosa_inicial   : float
        hba1c_inicial     : float
        diagnosticado_dm  : bool
    """
    grupo  = _grupo_enfermedad(edad)
    sexo_k = sexo if sexo in ['Masculino', 'Femenino'] else 'Otro'

    # ------------------------------------------------------------------
    # 1. DIABETES TIPO 2
    #    P = prob_base(edad) × factor_IMC × factor_actividad
    # ------------------------------------------------------------------
    prob_dm = (
        PROB_DIABETES_BASE[grupo] *
        FACTOR_DIABETES_IMC.get(estado_nutricional, 1.0) *
        FACTOR_DIABETES_ACTIVIDAD.get(actividad_fisica, 1.0)
    )
    tiene_dm = random.random() < min(prob_dm, 1.0)
    diabetes = 'Sí' if tiene_dm else 'No'

    # Momento del diagnóstico y valores iniciales para AR(1)
    if tiene_dm:
        info_dx          = _asignar_momento_diagnostico(edad)
        momento_dx       = info_dx['momento']
        glucosa_inicial  = info_dx['glucosa_inicial']
        hba1c_inicial    = info_dx['hba1c_inicial']
        diagnosticado_dm = info_dx['diagnosticado']
    else:
        momento_dx       = None
        glucosa_inicial  = round(random.uniform(70, 99), 1)
        hba1c_inicial    = round(random.uniform(4.0, 5.6), 1)
        diagnosticado_dm = False

    # ------------------------------------------------------------------
    # 2. HIPERTENSIÓN ARTERIAL
    #    Si tiene DM2 → P(HTA|DM2) = 46% (ENSA 2004 CDMX)
    #    Si no tiene  → prob_base(edad, sexo) (ENSANUT 2022)
    # ------------------------------------------------------------------
    if tiene_dm:
        prob_hta = PROB_HTA_DADO_DM2
    else:
        prob_hta = PROB_HIPERTENSION_BASE[grupo][sexo_k]

    tiene_hta    = random.random() < min(prob_hta, 1.0)
    hipertension = 'Sí' if tiene_hta else 'No'

    # ------------------------------------------------------------------
    # 3. DISLIPIDEMIA (HIPERCOLESTEROLEMIA)
    #    Si tiene DM2 → 55.2% INDEPENDIENTE del IMC (ENSA 2004 Tabla V)
    #    Si tiene HTA sin DM2 → 52.5% (ENSA 2004 Tabla I)
    #    Si no tiene ninguna  → depende del IMC (ENSA 2004 Tabla I)
    # ------------------------------------------------------------------
    if tiene_dm:
        # En diabéticos el IMC no cambia significativamente el riesgo de HCL
        prob_hcl = PROB_HCL_DADO_DM2
    elif tiene_hta:
        prob_hcl = PROB_HCL_DADO_HTA_SIN_DM2
    else:
        prob_hcl = PROB_HCL_SIN_DM2_POR_IMC.get(estado_nutricional, 0.40)

    tiene_hcl    = random.random() < min(prob_hcl, 1.0)
    dislipidemia = 'Sí' if tiene_hcl else 'No'

    return {
        'diabetes':         diabetes,
        'hipertension':     hipertension,
        'dislipidemia':     dislipidemia,
        'momento_dx':       momento_dx,
        'glucosa_inicial':  glucosa_inicial,
        'hba1c_inicial':    hba1c_inicial,
        'diagnosticado_dm': diagnosticado_dm,
    }