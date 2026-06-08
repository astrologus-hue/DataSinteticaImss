# personas/historia_clinica.py
"""
Módulo de generación de Historia Clínica.
Componente del Expediente Clínico — NOM-004-SSA3-2012.

Genera los antecedentes personales patológicos y no patológicos,
y los antecedentes heredofamiliares del paciente.

NO modela evolución temporal — es información estática del paciente
al momento de su primer contacto con el sistema de salud.

Fuentes estadísticas:
    ENSANUT 2022  — tabaquismo: 19.5% activo, 17.8% ex-fumador
    ENSANUT 2022  — alcohol: 55.5% consume, 40.4% consumo excesivo
    ENSANUT 2012  — antecedente familiar DM2:
                    54.46% en diabéticos vs 34.81% en no diabéticos
    ENSANUT Gto 2022 / ENSANUT 2018-19
                  — antecedente familiar HTA:
                    ~49.6% en hipertensos vs ~31.4% en no hipertensos

Campos generados:
    Antecedentes heredofamiliares:
        antecedente_familiar_dm2  : Sí | No
        antecedente_familiar_hta  : Sí | No

    Antecedentes personales no patológicos:
        tabaquismo                : Nunca | Activo | Ex-fumador
        alcoholismo               : No consume | Consume | Excesivo
"""
import random
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config


# ===========================================================================
# PARÁMETROS — ANTECEDENTES HEREDOFAMILIARES
# ===========================================================================

# Probabilidad de antecedente familiar de DM2
# Fuente: ENSANUT 2012 — adultos México
#   54.46% de diabéticos tienen padre/madre con DM2
#   34.81% de no diabéticos tienen padre/madre con DM2
PROB_ANTECEDENTE_DM2 = {
    'con_dm2':  0.5446,
    'sin_dm2':  0.3481,
}

# Probabilidad de antecedente familiar de HTA
# Fuente: ENSANUT Gto 2022 — 31.4% población general
#         ENSANUT 2018-19 — 49.6% en hipertensos
PROB_ANTECEDENTE_HTA = {
    'con_hta':  0.496,
    'sin_hta':  0.314,
}


# ===========================================================================
# PARÁMETROS — TABAQUISMO
# Fuente: ENSANUT Continua 2022
#   19.5% fuma actualmente
#   17.8% fumó en el pasado (ex-fumador)
#   62.7% nunca ha fumado (complemento)
# ===========================================================================
PROB_TABAQUISMO = {
    'Activo':     0.195,
    'Ex-fumador': 0.178,
    'Nunca':      0.627,
}


# ===========================================================================
# PARÁMETROS — ALCOHOLISMO
# Fuente: ENSANUT Continua 2022
#   55.5% consume alcohol actualmente
#   De los que consumen: 40.4% tiene consumo excesivo en últimos 12 meses
#   44.5% no consume
#
# Distribución final:
#   No consume : 44.5%
#   Consume    : 55.5% × (1 - 0.404) = 33.1%
#   Excesivo   : 55.5% × 0.404       = 22.4%
# ===========================================================================
PROB_ALCOHOLISMO = {
    'No consume': 0.445,
    'Consume':    0.331,
    'Excesivo':   0.224,
}


# ===========================================================================
# FUNCIÓN PRINCIPAL
# ===========================================================================

def generar_historia_clinica(diabetes: str, hipertension: str) -> dict:
    """
    Genera la historia clínica del paciente con antecedentes
    heredofamiliares y personales no patológicos.

    La probabilidad de antecedente familiar se modula según si
    el paciente ya tiene la enfermedad — coherente con la
    agregación familiar documentada en el ENSANUT.

    Parámetros
    ----------
    diabetes     : str — 'Sí' | 'No'
    hipertension : str — 'Sí' | 'No'

    Retorna
    -------
    dict:
        antecedente_familiar_dm2 : Sí | No
        antecedente_familiar_hta : Sí | No
        tabaquismo               : Nunca | Activo | Ex-fumador
        alcoholismo              : No consume | Consume | Excesivo
    """

    # ------------------------------------------------------------------
    # 1. ANTECEDENTE FAMILIAR DM2
    #    Si el paciente tiene DM2 → mayor probabilidad de familiar con DM2
    #    Fuente: ENSANUT 2012
    # ------------------------------------------------------------------
    prob_dm2_fam = PROB_ANTECEDENTE_DM2['con_dm2'] if diabetes == 'Sí' \
                   else PROB_ANTECEDENTE_DM2['sin_dm2']
    antecedente_dm2 = 'Sí' if random.random() < prob_dm2_fam else 'No'

    # ------------------------------------------------------------------
    # 2. ANTECEDENTE FAMILIAR HTA
    #    Si el paciente tiene HTA → mayor probabilidad de familiar con HTA
    #    Fuente: ENSANUT Gto 2022 / ENSANUT 2018-19
    # ------------------------------------------------------------------
    prob_hta_fam = PROB_ANTECEDENTE_HTA['con_hta'] if hipertension == 'Sí' \
                   else PROB_ANTECEDENTE_HTA['sin_hta']
    antecedente_hta = 'Sí' if random.random() < prob_hta_fam else 'No'

    # ------------------------------------------------------------------
    # 3. TABAQUISMO
    #    Fuente: ENSANUT Continua 2022
    #    19.5% activo | 17.8% ex-fumador | 62.7% nunca
    # ------------------------------------------------------------------
    tabaquismo = random.choices(
        list(PROB_TABAQUISMO.keys()),
        weights=list(PROB_TABAQUISMO.values()),
        k=1
    )[0]

    # ------------------------------------------------------------------
    # 4. ALCOHOLISMO
    #    Fuente: ENSANUT Continua 2022
    #    44.5% no consume | 33.1% consume | 22.4% excesivo
    # ------------------------------------------------------------------
    alcoholismo = random.choices(
        list(PROB_ALCOHOLISMO.keys()),
        weights=list(PROB_ALCOHOLISMO.values()),
        k=1
    )[0]

    return {
        'antecedente_familiar_dm2': antecedente_dm2,
        'antecedente_familiar_hta': antecedente_hta,
        'tabaquismo':               tabaquismo,
        'alcoholismo':              alcoholismo,
    }